-- ClearGlass RFED(TM) ledger: append-only, hash-chained record of every
-- model-influenced decision. Run inside the client's Supabase/Postgres project
-- before go-live. Mirrors bots/rfed_audit_bot.py — keep the two in step.

create table if not exists rfed_records (
    -- identity
    record_id       uuid primary key,
    occurred_at     timestamptz not null default now(),
    policy_version  text        not null,

    -- R — Request
    actor           text not null,              -- 'n8n:rfed-audit-trail' | 'cursor:agent' | human email
    workflow        text not null,              -- 'client_zero_trust' | 'rfed_audit_trail' | ...
    action          text not null,              -- key into ACTION_RISK
    target          text not null,              -- endpoint id, ticket id, client slug
    intent          text not null default '',
    correlation_id  text not null default '',
    input_digest    text not null default '',   -- sha256 of the raw inbound payload

    -- F — Facts (array of {source, reference, content_digest, retrieved_at, trusted})
    facts           jsonb not null default '[]'::jsonb,

    -- E — Evidence
    model_id        text not null,              -- exact model id, never a marketing name
    provider        text not null default 'anthropic',
    temperature     numeric(4,3) not null default 0,
    max_tokens      integer not null default 0,
    prompt_digest   text not null default '',
    output_digest   text not null default '',
    output_excerpt  text not null default '',   -- redacted + truncated for human review
    confidence      numeric(4,3) not null default 1,
    citations       jsonb not null default '[]'::jsonb,
    input_tokens    integer not null default 0,
    output_tokens   integer not null default 0,

    -- D — Decision
    score             integer not null check (score between 0 and 100),
    tier              text    not null check (tier in ('low','medium','high','critical')),
    route             text    not null check (route in ('auto_executed','queued_for_approval','blocked')),
    requires_approval boolean not null default false,
    reasons           jsonb   not null default '[]'::jsonb,
    approved_by       text,
    approved_at       timestamptz,

    -- chain
    prev_hash       text not null,
    chain_hash      text not null unique
);

create index if not exists rfed_records_workflow_idx    on rfed_records (workflow, occurred_at desc);
create index if not exists rfed_records_target_idx      on rfed_records (target);
create index if not exists rfed_records_correlation_idx on rfed_records (correlation_id);
create index if not exists rfed_records_route_idx       on rfed_records (route, occurred_at desc);
create index if not exists rfed_records_prev_hash_idx   on rfed_records (prev_hash);

-- ---------------------------------------------------------------------------
-- Append-only enforcement. The ledger is evidence; evidence does not change.
-- ---------------------------------------------------------------------------
create or replace function rfed_records_append_only()
returns trigger as $$
begin
    if tg_op = 'DELETE' then
        raise exception 'rfed_records is append-only; deletes are not allowed';
    end if;
    raise exception 'rfed_records is append-only; updates are not allowed (record approvals as new rows)';
end;
$$ language plpgsql;

drop trigger if exists rfed_records_append_only_t on rfed_records;
create trigger rfed_records_append_only_t
    before update or delete on rfed_records
    for each row execute function rfed_records_append_only();

-- ---------------------------------------------------------------------------
-- Chain enforcement. A new row must extend the current head, so a writer cannot
-- splice a record into the middle of history or fork the chain.
-- ---------------------------------------------------------------------------
create or replace function rfed_records_chain_guard()
returns trigger as $$
declare
    current_head text;
begin
    select chain_hash into current_head
      from rfed_records
     order by occurred_at desc, ctid desc
     limit 1;

    if current_head is null then
        if new.prev_hash <> repeat('0', 64) then
            raise exception 'first rfed_records row must carry the genesis prev_hash';
        end if;
    elsif new.prev_hash <> current_head then
        raise exception 'rfed_records chain break: prev_hash % does not match head %',
            left(new.prev_hash, 12), left(current_head, 12);
    end if;

    return new;
end;
$$ language plpgsql;

drop trigger if exists rfed_records_chain_guard_t on rfed_records;
create trigger rfed_records_chain_guard_t
    before insert on rfed_records
    for each row execute function rfed_records_chain_guard();

-- ---------------------------------------------------------------------------
-- Grounding sources. The workflow retrieves facts *only* from this allow-list,
-- so the set of things a model can be told is itself governed. `trusted = false`
-- marks anything user- or internet-supplied; the governor scans those for
-- prompt-injection markers and gates on a hit.
-- ---------------------------------------------------------------------------
create table if not exists rfed_fact_sources (
    id             uuid primary key default gen_random_uuid(),
    target         text not null,              -- the asset this fact grounds
    source         text not null,              -- 'pg:endpoints', 'web:vendor-advisory', ...
    reference      text not null,              -- row id, URL, file path
    content_digest text not null,              -- sha256 of the retrieved content
    retrieved_at   timestamptz not null default now(),
    trusted        boolean not null default false,
    active         boolean not null default true,
    unique (target, source, reference)
);

create index if not exists rfed_fact_sources_target_idx on rfed_fact_sources (target, active);

-- ---------------------------------------------------------------------------
-- Approval queue. Rows here are *pointers* into the ledger, not the record of
-- truth: approving writes a new rfed_records row (see bots/rfed_audit_bot.py
-- :approve). This table exists so the operator UI has something to poll.
-- ---------------------------------------------------------------------------
create table if not exists rfed_approvals (
    id            uuid primary key default gen_random_uuid(),
    record_id     uuid not null references rfed_records (record_id),
    requested_at  timestamptz not null default now(),
    status        text not null default 'pending'
                  check (status in ('pending','approved','rejected','expired')),
    decided_by    text,
    decided_at    timestamptz,
    rationale     text,
    -- an approval that is never answered must expire closed, not hang open
    expires_at    timestamptz not null default now() + interval '24 hours'
);

create index if not exists rfed_approvals_status_idx on rfed_approvals (status, requested_at);

-- Convenience view: what is waiting on a human right now.
create or replace view rfed_pending_approvals as
select a.id             as approval_id,
       a.requested_at,
       a.expires_at,
       r.record_id,
       r.workflow,
       r.action,
       r.target,
       r.tier,
       r.score,
       r.model_id,
       r.output_excerpt,
       r.reasons
  from rfed_approvals a
  join rfed_records   r on r.record_id = a.record_id
 where a.status = 'pending'
   and a.expires_at > now()
 order by r.score desc, a.requested_at asc;

-- Convenience view: model accountability rollup for the client's evidence pack.
create or replace view rfed_model_accountability as
select model_id,
       policy_version,
       count(*)                                             as decisions,
       count(*) filter (where route = 'auto_executed')       as auto_executed,
       count(*) filter (where route = 'queued_for_approval') as queued,
       count(*) filter (where route = 'blocked')             as blocked,
       count(*) filter (where jsonb_array_length(citations) = 0) as ungrounded,
       count(*) filter (where approved_by is not null)       as human_approved,
       round(avg(confidence), 3)                             as mean_confidence,
       max(occurred_at)                                      as last_seen
  from rfed_records
 group by model_id, policy_version;

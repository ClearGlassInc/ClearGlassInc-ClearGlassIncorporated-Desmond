-- CashPulse audit log: append-only record of every bot action.
-- Run inside the client's Supabase project before go-live.

create table if not exists bot_actions (
    id            uuid primary key default gen_random_uuid(),
    occurred_at   timestamptz not null default now(),
    actor         text not null,                 -- 'cashpulse-bot' or human approver
    workflow      text not null,                 -- 'lead_capture' | 'invoice_dunning' | ...
    action        text not null,                 -- 'send_email' | 'create_payment_link' | ...
    target        text not null,                 -- invoice_id, lead_email, meeting_id, ...
    payload_hash  text not null,                 -- sha256(payload) for replay/forensics
    requires_approval boolean not null default false,
    approved_by   text,
    approved_at   timestamptz,
    status        text not null default 'recorded',
    error         text
);

create index if not exists bot_actions_workflow_idx on bot_actions (workflow, occurred_at desc);
create index if not exists bot_actions_target_idx   on bot_actions (target);

-- Append-only enforcement: prevent updates/deletes on historical rows.
create or replace function bot_actions_no_mutate()
returns trigger as $$
begin
    if tg_op = 'DELETE' then
        raise exception 'bot_actions is append-only; deletes are not allowed';
    end if;
    if tg_op = 'UPDATE' and old.status = 'recorded' and new.status not in ('approved', 'failed') then
        raise exception 'bot_actions rows can only transition to approved or failed';
    end if;
    return new;
end;
$$ language plpgsql;

drop trigger if exists bot_actions_no_mutate_t on bot_actions;
create trigger bot_actions_no_mutate_t
    before update or delete on bot_actions
    for each row execute function bot_actions_no_mutate();

-- Suppression list: unsubscribed contacts must never receive outbound.
create table if not exists bot_suppression (
    contact     text primary key,           -- email or E.164 phone
    reason      text not null,
    suppressed_at timestamptz not null default now()
);

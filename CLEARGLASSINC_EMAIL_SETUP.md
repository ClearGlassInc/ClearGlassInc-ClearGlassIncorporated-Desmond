# ClearGlassInc Artemis custom-domain email runbook

> **Scope:** establish the production mailbox `desmond@clearglassinc.com` without changing the website hosted on the same domain. This is an operator runbook, not evidence that any provider, tenant, DNS record, or security control is currently configured.

## Exact outcome and shortest safe path

Owning `clearglassinc.com` is necessary, but it does not itself create a mailbox. The domain must be connected to a mail host, and the mail host must contain a licensed user whose primary address is `desmond@clearglassinc.com`.

Email domain names and, in normal hosted-mail operation, mailbox addressing are case-insensitive. Configure and publish the canonical address in lowercase as `desmond@clearglassinc.com`; messages addressed as `Desmond@clearglassinc.com` should reach the same mailbox, while the lowercase form avoids inconsistent display, forms, and documentation.

The recommended implementation is:

1. Buy **Microsoft 365 Business Premium** directly from Microsoft for one user. Do not buy a second domain during checkout.
2. Create the temporary Microsoft tenant and protect its administrator with phishing-resistant MFA.
3. In the Microsoft 365 admin center, add the existing domain `clearglassinc.com` and copy Microsoft's unique verification TXT record into the domain's authoritative DNS console.
4. After verification, create the user **Desmond**, set the username and primary address to `desmond@clearglassinc.com`, and assign the Exchange-containing licence.
5. Copy the tenant-specific MX, SPF, Autodiscover, and DKIM values shown by Microsoft into DNS. Preserve all website records; only replace obsolete mail records.
6. Enable DKIM, publish DMARC initially at `p=none`, and test inbound and outbound delivery before tightening DMARC.

Do not copy another tenant's MX, verification, or DKIM targets from this document or a tutorial. Those values are generated for the specific Microsoft tenant. DNS changes are the only part performed at the registrar or DNS provider; mailbox creation and security configuration happen in Microsoft 365.

### Completion checklist

The setup is complete only when all of the following are true:

- `desmond@clearglassinc.com` can sign in at Outlook on the web with MFA.
- External test accounts can send to the mailbox and receive replies.
- A received test message reports aligned `spf=pass`, `dkim=pass`, and `dmarc=pass` in its authentication results.
- Existing `clearglassinc.com` website records and GitHub Pages routing still resolve normally.
- Recovery accounts, DNS rollback values, and tenant ownership are recorded in the approved credential/recovery system—not in this repository.

## 1. Choose the provider and approve the spend

> **Pricing snapshot (USD vendor list prices represented by this runbook; taxes, region, promotions, monthly-commitment premiums, and future changes are excluded):** verify the price shown in the checkout cart before purchase. Annual-commitment prices are normalized per user/month below; do not treat this document as a quote.

| Recommended plan | Approx. USD/user/month | Mailbox and integration | Security/admin fit | Principal trade-off |
| --- | ---: | --- | --- | --- |
| [Microsoft 365 Business Premium](https://www.microsoft.com/en-us/microsoft-365/business/compare-all-microsoft-365-business-products) | **$22.00** with annual commitment | 50 GB Exchange mailbox, desktop/web/mobile Outlook and Microsoft 365 apps | Entra ID, Conditional Access, Intune, Defender for Business and Defender for Office 365 Plan 1 make this the strongest one-product baseline | Highest cost and administrative complexity of these choices |
| [Google Workspace Business Standard](https://workspace.google.com/pricing.html) | **$14.00** with one-year commitment | Gmail plus 2 TB pooled storage per user; Outlook interoperability, but Gmail web is the native client | Strong Google identity/admin, Vault is not included at Standard, and endpoint/retention controls differ by edition | Google Workspace Sync for Microsoft Outlook is Windows-only; Mac Outlook normally uses Google OAuth/IMAP semantics rather than native Exchange behavior |
| [Zoho Mail Premium](https://www.zoho.com/mail/zohomail-pricing.html) | **$4.00** billed annually | 50 GB mail storage plus archival/eDiscovery features advertised for this tier; IMAP/POP/ActiveSync availability must be checked for the purchased region/tier | Low cost and useful mail administration, but a smaller security, endpoint, and enterprise integration ecosystem | Outlook experience and advanced controls are less integrated; regional data-center DNS values differ |

Prices and entitlements are plan-, country-, and date-sensitive. If a vendor checkout contradicts this table, stop and update the decision record rather than silently accepting a different product. Google also sells Business Plus (approximately $22/user/month annually) when Vault and stronger endpoint controls are needed; at that price, Microsoft remains the cleaner Outlook-first choice.

**Decision: use Microsoft 365 Business Premium for ClearGlassInc Artemis.** It gives a small security-focused company hosted Exchange, first-class Outlook support, Microsoft Entra ID, Conditional Access, Intune, and the stronger Defender capabilities in one operational boundary.

Business Basic or Standard can host the same domain at lower cost, but Premium is the appropriate baseline when device posture, phishing resistance, endpoint defense, and Outlook are requirements. Do not choose only on mailbox price: retention, eDiscovery, audit duration, endpoint control, support, data residency, and recovery are part of the effective cost.

## 2. Prepare the DNS cutover and rollback

### Operator acceptance criteria

- [ ] The authoritative DNS operator, Microsoft tenant owner, billing owner, security owner, and rollback owner are named.
- [ ] The existing zone is exported and its website records are marked **do not change**.
- [ ] Every service that sends mail as `@clearglassinc.com` is inventoried.
- [ ] A one-user Business Premium subscription is approved and checkout price/term recorded.
- [ ] The mailbox works internally before MX cutover and externally after it.
- [ ] SPF, DKIM, and DMARC pass with aligned `clearglassinc.com` identifiers.

## Preconditions and change plan

1. Identify the **authoritative DNS host** for `clearglassinc.com` (the nameservers shown by `dig NS clearglassinc.com`), and sign in using a phishing-resistant administrator identity.
2. Export or screenshot the current DNS zone. Record the previous mail provider, existing MX/TXT/CNAME records, and rollback owner.
3. Inventory every legitimate sender using `@clearglassinc.com`: Microsoft 365, website forms, CRM, ticketing, monitoring, and bulk-mail platforms. SPF and DKIM must cover each one, preferably with bulk/transactional mail isolated on a subdomain.
4. Lower the TTL of mail-related records to approximately 300 seconds at least one old-TTL interval before the cutover. Do **not** remove website `A`, `AAAA`, `CNAME`, `CNAME`/Pages, or verification records unrelated to mail.
5. Create and test the mailbox before changing MX. Schedule the cutover during a monitored window; retain access to the old mailbox until migration and rollback windows close.

## 3. Create and secure the Microsoft 365 tenant

Microsoft's admin wizard is the source of truth for tenant-specific record values. Labels shown below are examples; copy the exact values displayed for the tenant rather than guessing them.

### 3.1 Buy the subscription and protect the bootstrap administrator

1. Open the official Microsoft 365 business plan comparison, select **Microsoft 365 Business Premium**, choose **1 user**, and choose the desired annual or monthly commitment. Use company-controlled billing/recovery details and buy **no additional domain**.
2. Complete checkout and choose the initial tenant name. Microsoft creates an `*.onmicrosoft.com` namespace and bootstrap administrator; record the tenant ID, subscription term, renewal owner, and recovery procedure in the approved secrets/operations system.
3. Sign in to [admin.microsoft.com](https://admin.microsoft.com) with the bootstrap account and confirm **Billing → Your products** shows one active Business Premium licence. The initial account uses an `*.onmicrosoft.com` address.
4. Create two dedicated cloud-only emergency administrator accounts on `*.onmicrosoft.com`; exclude only those accounts from Conditional Access, protect each with separate hardware security keys, alert on their use, and do not use them for email or daily work.
5. Create a separate named administrator account for routine administration. Do not give the future daily mailbox permanent Global Administrator privileges.
6. Register at least two strong authentication methods before changing the domain or access policies.

### 3.2 Add and verify `clearglassinc.com`

1. Open the [Microsoft 365 admin center](https://admin.microsoft.com), then **Settings → Domains → Add domain**.
2. Enter `clearglassinc.com`.
3. Select manual DNS setup. Microsoft supplies a verification TXT record similar to:

   ```dns
   Type: TXT
   Host/Name: @
   Value: MS=ms########
   TTL: 300 (or provider default)
   ```

4. Add that exact TXT value at the authoritative DNS host. Keep unrelated TXT records; a domain can have multiple TXT records.
5. Return to the wizard and select **Verify**. DNS propagation is not instantaneous, so retry after confirming the authoritative nameservers return the value.
6. Select only the Microsoft services actually being deployed. Do not delegate nameservers to Microsoft merely to configure email.

### 3.3 Create `desmond@clearglassinc.com`

1. In **Users → Active users → Add a user**, enter **Desmond** as the display name and select `clearglassinc.com` as the domain.
2. Set the username and primary address to `desmond@clearglassinc.com`. Avoid using a shared role address as the person's sign-in identity.
3. Set the user's **Usage location**, assign the available **Microsoft 365 Business Premium** licence, and leave Exchange Online enabled. Generate a temporary random password, select forced password change at first sign-in, deliver it out of band, and never commit it.
4. In the user's **Mail** tab, verify the primary SMTP address is exactly `desmond@clearglassinc.com`; add capitalized display text only in the display name, not as a second mailbox.
5. Have Desmond sign in at [mysignins.microsoft.com/security-info](https://mysignins.microsoft.com/security-info), replace the temporary password, and register at least two methods, preferably a passkey/FIDO2 security key plus Microsoft Authenticator.
6. Create role addresses such as `security@`, `billing@`, or `support@` as shared mailboxes where appropriate. Grant named users access; do not share passwords.
7. Send a test message internally while MX still points to the old provider.

## 4. Publish DNS mail and authentication records

At the DNS provider that is authoritative for the nameservers—not necessarily the registrar—open its equivalent of **Domains → `clearglassinc.com` → DNS / Zone management → Add record**. Use `@` for the zone apex when supported (some consoles require a blank name), enter host labels rather than duplicating the domain, leave CDN/proxying disabled for mail records, and do not edit GitHub Pages/web records.

In Microsoft 365, open **Settings → Domains → `clearglassinc.com` → DNS records** and copy the values Microsoft currently displays. A typical Exchange Online configuration has this shape:

| Purpose | Type | Host | Value | Priority |
| --- | --- | --- | --- | --- |
| Inbound mail | MX | `@` | tenant-specific `…mail.protection.outlook.com` target | `0` or the lowest numeric value |
| Sender Policy Framework | TXT | `@` | `v=spf1 include:spf.protection.outlook.com -all` | — |
| Autodiscover | CNAME | `autodiscover` | `autodiscover.outlook.com` | — |
| DKIM selector 1 | CNAME | `selector1._domainkey` | tenant-specific target shown by Microsoft | — |
| DKIM selector 2 | CNAME | `selector2._domainkey` | tenant-specific target shown by Microsoft | — |

Apply these controls deliberately:

1. **MX:** remove obsolete MX records when cutting over. Multiple providers' MX records are not a migration strategy; they can split or misroute delivery. Do not place an HTTP/CDN proxy in front of mail DNS records.
2. **SPF:** publish **one** SPF TXT record at the root. If other services send as the root domain, merge their documented `include` mechanisms into the same record. Keep DNS lookups within SPF's limit; do not create several `v=spf1` records. End with `-all` after all senders are inventoried.
3. **DKIM:** unlike providers that publish a selector TXT public key, Exchange Online gives this custom domain **two CNAME records**, not a hand-authored TXT value. The exact targets cannot exist until Microsoft knows both the verified domain and tenant; obtain them in **Microsoft Defender portal → Email & collaboration → Policies & rules → Threat policies → Email authentication settings → DKIM → `clearglassinc.com`** (or the current equivalent), select the domain, and copy both values from the error/publish prompt. Add both CNAME selectors, wait until they resolve publicly, then return and enable signing. Do not invent a selector or copy a target from another tenant. Send a message and confirm the header reports `dkim=pass`. Microsoft rotates between the two selectors; retain both.
4. **DMARC:** start with reporting mode only after SPF and DKIM pass:

   ```dns
   Type: TXT
   Host/Name: _dmarc
   Value: v=DMARC1; p=none; pct=100; rua=mailto:dmarc@clearglassinc.com; adkim=s; aspf=s
   ```

   Create and monitor `dmarc@clearglassinc.com` (or use a reputable DMARC reporting service). Aggregate reports are XML and can expose mail-flow metadata, so restrict access and retention. Some external reporting services require destination authorization records.
5. Review reports for all legitimate services and forwarding behavior. Progress in controlled stages from `p=none` to `p=quarantine; pct=10`, increase `pct`, then use `p=reject; pct=100`. A final strict policy can be:

   ```dns
   v=DMARC1; p=reject; pct=100; rua=mailto:dmarc@clearglassinc.com; adkim=s; aspf=s
   ```

6. Consider publishing `sp=reject` only after every subdomain sender is inventoried. Consider MTA-STS/TLS-RPT after mail flow is stable; they are useful additional transport controls, not substitutes for SPF, DKIM, or DMARC.

### 4.1 Validate DNS before declaring the cutover complete

Query the authoritative and public DNS views:

```bash
dig +short NS clearglassinc.com
dig +short MX clearglassinc.com
dig +short TXT clearglassinc.com
dig +short CNAME selector1._domainkey.clearglassinc.com
dig +short CNAME selector2._domainkey.clearglassinc.com
dig +short TXT _dmarc.clearglassinc.com
```

Then test messages in both directions with unrelated Microsoft, Google, and other external accounts. Inspect received headers for `spf=pass`, `dkim=pass`, and `dmarc=pass`, confirm alignment uses `clearglassinc.com`, and verify messages do not unexpectedly land in junk. Test reply, attachment, calendar invitation, shared mailbox, and password/MFA recovery paths. Keep the old service available until delayed mail, historical data, delegates, aliases, and mobile clients are accounted for.

## 5. Connect Outlook

### Outlook on the web

1. Visit [outlook.office.com](https://outlook.office.com).
2. Sign in with the full address, `Desmond@clearglassinc.com`.
3. Complete MFA registration and verify the expected ClearGlassInc Artemis tenant/organization context before approving a prompt.
4. Configure time zone, language, signature, and notification preferences. Do not create rules that automatically forward company mail to personal accounts.

### Outlook desktop (Windows or macOS)

1. Install a supported Microsoft 365 Apps/Outlook release from the signed-in Microsoft 365 portal or managed company deployment.
2. Choose **Add account**, enter the full custom-domain address, and use the Microsoft sign-in window. Autodiscover should configure Exchange automatically.
3. Complete MFA. Do not select POP/IMAP or manually enter SMTP credentials for a normal Exchange Online mailbox.
4. Confirm mail, calendar, contacts, search, and shared-mailbox access. If discovery fails, verify the licence, domain, `autodiscover` CNAME, client version, and Conditional Access sign-in logs before attempting manual configuration.

Modern Outlook uses OAuth/modern authentication. **Do not enable app passwords** for Outlook. App passwords exist only for narrowly approved legacy clients when legacy authentication is still allowed; replacing or retiring that client is safer.

### IMAP/SMTP exception (not the default)

Use native Exchange/Autodiscover whenever possible. If an approved application cannot use Microsoft Graph and must use mail protocols, explicitly enable only the required protocol for only its dedicated mailbox and require OAuth 2.0:

| Protocol | Host | Port | Encryption |
| --- | --- | ---: | --- |
| IMAP4 | `outlook.office365.com` | `993` | TLS |
| POP3 (avoid unless required) | `outlook.office365.com` | `995` | TLS |
| SMTP submission | `smtp.office365.com` | `587` | STARTTLS |

The username is the full mailbox address. Basic authentication and ordinary account passwords must not be used for automation. Prefer Microsoft Graph with application access restricted to the intended mailbox; never re-enable tenant-wide legacy authentication merely to satisfy a client.

## 6. Test and verify end to end

1. **DNS:** run the `dig` commands above against at least two public resolvers after propagation; compare the answers to the Microsoft admin center, not to examples in this file.
2. **Inbound:** send a new message from an unrelated Gmail or other external account to `desmond@clearglassinc.com`; verify delivery, timestamp, attachment, and reply threading.
3. **Outbound:** send a plain-text message and an attachment to unrelated Gmail and Microsoft recipients; confirm Inbox/Junk placement and inspect the recipients' **Show original / View source** authentication results.
4. **Authentication:** require `spf=pass`, `dkim=pass`, and `dmarc=pass`, with the DKIM `d=` or SPF MAIL FROM domain aligned to `clearglassinc.com`. A mere DNS-record check is not proof that signing or alignment works.
5. **Independent diagnostics:** use [Microsoft Remote Connectivity Analyzer](https://testconnectivity.microsoft.com/) for Exchange/Autodiscover, [MXToolbox](https://mxtoolbox.com/) or [Google Admin Toolbox Dig](https://toolbox.googleapps.com/apps/dig/) for public DNS, and [mail-tester](https://www.mail-tester.com/) for a supplementary deliverability report. Do not send sensitive content to third-party test services.
6. **Client/security:** test Outlook web and desktop sign-in, MFA, calendar invitation, contact sync, search, password recovery, quarantine release procedure, and sign-in/audit logs.
7. **Website regression:** load `https://clearglassinc.com`, check its certificate and key pages, and confirm the original web `A`/`AAAA`/`CNAME` records did not change.
8. **DMARC promotion:** monitor at least one representative mail cycle; remediate every legitimate sender, then stage `quarantine` and finally `reject`. Record the approver, effective time, and rollback record values.

## 7. Security and operations baseline

### Identity and privileged access

- Require phishing-resistant MFA (FIDO2/passkeys or certificate-based authentication) for administrators and prefer it for all users. SMS should be recovery-only where unavoidable.
- Use Conditional Access to require MFA, block legacy authentication, constrain risky sign-ins, and require compliant managed devices for administrative access. Build policies in report-only mode, examine results, exclude only monitored emergency accounts, and stage enforcement to avoid lockout.
- Separate daily and privileged accounts. Apply least-privilege roles and use time-bound privileged activation where the subscription supports it.
- Disable sign-in and revoke sessions immediately during offboarding; preserve or delegate the mailbox according to the retention policy.
- Configure self-service password reset with strong methods and alerts. Review authentication-method registration and privileged-role assignments regularly.

### Mail and collaboration

- Keep Exchange Online Protection anti-phishing, anti-malware, Safe Links, and Safe Attachments capabilities enabled as licensed. Protect executives and look-alike domains, but test impersonation policy before enforcement.
- Disable automatic external forwarding by default. Restrict inbox-rule creation and SMTP AUTH to justified exceptions; disable POP and IMAP unless a documented application needs them.
- Use shared mailboxes or groups for role identities. Never share user credentials, MFA factors, or application secrets.
- Establish retention, legal hold, and deletion rules based on business/legal requirements rather than indefinite default retention.
- Treat Microsoft service retention as distinct from an independent backup. Define recovery-point/recovery-time requirements; then either use a reviewed Microsoft 365 backup product with encryption, immutable retention, tested restore, and least-privilege access, or perform documented periodic eDiscovery/PST exports where legally and operationally appropriate. Test restoration quarterly. Do not rely on Outlook's cached OST file as a backup.
- Separate marketing and machine-generated mail onto controlled subdomains (for example, `notify.clearglassinc.com`) with their own SPF, DKIM, DMARC, credentials, rate limits, and reputation.
- Review message trace, quarantines, forwarding rules, consent grants, anomalous sign-ins, and administrator audit events. Send alerts to an independently monitored security channel.

### Applications and AI integrations

- Prefer OAuth with administrator-reviewed, least-privilege scopes. Do not give AI assistants full mailbox access merely for convenience.
- Treat email body, attachments, calendar content, and retrieved links as untrusted input. An AI agent must not execute instructions found in mail, send messages, open cases, or disclose data without deterministic policy checks and the required human approval.
- Use a dedicated service principal or mailbox per integration, restrict it to specific mailboxes where supported, rotate/revoke credentials, and log reads, drafts, approvals, and sends without logging message contents unnecessarily.
- Block user consent to unverified or high-privilege applications; use an audited admin-consent workflow. Periodically remove unused enterprise applications and delegated grants.

## 8. Alternative-provider execution notes

If a different provider is selected, retain the same staged cutover and security model but use only the records generated for that account and region:

1. Add `clearglassinc.com` in the provider's administrator console and verify ownership with its unique TXT record.
2. Create the licensed user/mailbox before switching MX.
3. Replace old MX records with the provider's **current** documented MX set. Google Workspace and Zoho values can differ from historical examples or by Zoho data-center region; never copy records from an unrelated tutorial.
4. Publish a single root SPF policy containing that provider's current include plus every other authorized sender.
5. Generate DKIM in the admin console, publish the generated selector TXT/CNAME, verify it, and explicitly start DKIM signing if the provider requires that second step.
6. Publish DMARC at `_dmarc`, monitor alignment, and move gradually to rejection.
7. For Outlook, use the provider-supported OAuth account flow. Google Workspace Sync for Microsoft Outlook is edition/platform dependent; Zoho's Exchange ActiveSync/IMAP availability is plan dependent. Confirm support before purchasing.

Authoritative setup references:

- [Microsoft: add a custom domain](https://learn.microsoft.com/en-us/microsoft-365/admin/setup/add-domain)
- [Microsoft: DNS records for Microsoft 365](https://learn.microsoft.com/en-us/microsoft-365/enterprise/external-domain-name-system-records)
- [Microsoft: DKIM for custom domains](https://learn.microsoft.com/en-us/defender-office-365/email-authentication-dkim-configure)
- [Microsoft: DMARC for outbound mail](https://learn.microsoft.com/en-us/defender-office-365/email-authentication-dmarc-configure)
- [Google Workspace: activate Gmail with MX records](https://support.google.com/a/answer/174125)
- [Google Workspace: SPF, DKIM, and DMARC](https://support.google.com/a/topic/2759254)
- [Zoho Mail: domain setup](https://www.zoho.com/mail/help/adminconsole/domains.html)
- [Zoho Mail: email authentication](https://www.zoho.com/mail/help/adminconsole/email-authentication.html)

## 9. Rollback and ownership

If inbound delivery fails, first verify authoritative DNS, record syntax, and provider service health. If recovery will exceed the agreed outage budget, restore the exported prior MX records and TTLs, confirm the old provider accepts mail, and investigate without repeatedly alternating MX. DNS rollback does not move messages already accepted by the new provider.

Assign named owners for tenant administration, DNS, billing, security monitoring, mailbox recovery, retention, and incident response. Store recovery codes and domain-registrar recovery material in an access-controlled offline system. Revalidate DNS authentication after adding any sender and at least quarterly.

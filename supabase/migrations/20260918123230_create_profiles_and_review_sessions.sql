-- Auth/permission structure: backs the roles already returned by NextAuth (web/src/auth.ts)
-- with real rows instead of only two env-var passwords. Login itself stays on NextAuth
-- Credentials for now; this table is the source of truth for "who is owner vs member".
create table if not exists public.profiles (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  role text not null default 'member' check (role in ('owner', 'member')),
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
-- No policies: anon/publishable and authenticated roles get zero access.
-- Only the secret (service_role) key, used server-side only, can read/write this table.

insert into public.profiles (email, role)
values ('douglas.morauer@paytrack.com.br', 'owner')
on conflict (email) do update set role = excluded.role;

-- Persisted review sessions: the server-side evolution of the existing "Salvar revisão" /
-- "Abrir revisão" feature (web/src/app/page.tsx saveSession()/openSession()), which today
-- only round-trips through a downloaded JSON file. Schema only — the app is NOT yet wired
-- to read/write this table.
create table if not exists public.review_sessions (
  id uuid primary key default gen_random_uuid(),
  owner_email text not null references public.profiles (email),
  file_name text,
  status text not null default 'in_progress' check (status in ('in_progress', 'exported')),
  -- Aggregate, non-sensitive counts (record counts, pending counts) for list views.
  summary jsonb not null default '{}'::jsonb,
  -- Full session payload (converted loads, hierarchy, decisions). This is where customer
  -- PII (CPF, e-mail, birth date, RG, CNH, bank data) would land once/if the app is wired
  -- to persist here instead of only a locally downloaded file — flagged in ARCHITECTURE.md
  -- as a decision that changes today's "processed only in the browser" privacy posture.
  payload jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.review_sessions enable row level security;
-- No policies: same as above, server-only access via the secret key.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists review_sessions_set_updated_at on public.review_sessions;
create trigger review_sessions_set_updated_at
  before update on public.review_sessions
  for each row
  execute function public.set_updated_at();

create index if not exists review_sessions_owner_email_idx on public.review_sessions (owner_email);

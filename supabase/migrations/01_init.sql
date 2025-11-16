create table if not exists series (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    slug text unique not null,
    created_at timestamptz default now()
);

create table if not exists chapters (
    id uuid primary key default gen_random_uuid(),
    series_id uuid references series(id),
    title text,
    status text not null default 'processing',
    progress integer not null default 0,
    created_at timestamptz default now()
);

create table if not exists characters (
    id uuid primary key default gen_random_uuid(),
    series_id uuid references series(id),
    speaker_key text not null,
    display_name text,
    voice_id text,
    created_at timestamptz default now(),
    unique(series_id, speaker_key)
);

create table if not exists bubbles (
    id uuid primary key default gen_random_uuid(),
    chapter_id uuid references chapters(id),
    page_index integer not null,
    payload jsonb not null,
    created_at timestamptz default now()
);


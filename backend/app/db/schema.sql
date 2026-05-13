create extension if not exists pgcrypto;
create extension if not exists vector;

do $$
begin
  create type sex as enum ('male', 'female', 'other', 'prefer_not_to_say');
exception
  when duplicate_object then null;
end $$;

do $$
begin
  create type activity_level as enum ('sedentary', 'light', 'moderate', 'active', 'very_active');
exception
  when duplicate_object then null;
end $$;

do $$
begin
  create type health_goal as enum ('weight_loss', 'weight_gain', 'weight_maintenance', 'muscle_gain', 'medical_diet');
exception
  when duplicate_object then null;
end $$;

do $$
begin
  create type chat_session_type as enum ('analyse', 'compare', 'rag_chat');
exception
  when duplicate_object then null;
end $$;

do $$
begin
  create type chat_role as enum ('user', 'assistant', 'system');
exception
  when duplicate_object then null;
end $$;

do $$
begin
  create type rag_source_type as enum ('knowledge', 'disease', 'user_memory', 'label_ocr');
exception
  when duplicate_object then null;
end $$;

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create table if not exists users (
  id uuid primary key,
  email text not null unique,
  full_name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint users_email_not_blank check (length(trim(email)) > 0),
  constraint users_full_name_not_blank check (length(trim(full_name)) > 0)
);

create table if not exists health_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references users(id) on delete cascade,
  age integer not null,
  weight_kg numeric(6,2) not null,
  height_cm numeric(6,2) not null,
  sex sex not null,
  activity_level activity_level not null,
  goal health_goal not null,
  allergies text[] not null default '{}',
  diseases jsonb not null default '[]'::jsonb,
  dietary_preferences text[] not null default '{}',
  nutrition_goals text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint health_profiles_age_range check (age between 1 and 120),
  constraint health_profiles_weight_range check (weight_kg > 0 and weight_kg <= 500),
  constraint health_profiles_height_range check (height_cm > 0 and height_cm <= 300)
);

create table if not exists chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  type chat_session_type not null,
  title text not null,
  label_image_url text,
  parsed_nutrition_json jsonb not null default '{}'::jsonb,
  session_summary text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chat_sessions_title_not_blank check (length(trim(title)) > 0)
);

create table if not exists chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references chat_sessions(id) on delete cascade,
  role chat_role not null,
  content text not null,
  image_url text,
  embedding vector(384),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint chat_messages_content_not_blank check (length(trim(content)) > 0)
);

create table if not exists rag_chunks (
  id uuid primary key default gen_random_uuid(),
  source text not null,
  source_url text,
  source_type rag_source_type not null default 'knowledge',
  chunk_text text not null,
  content text generated always as (chunk_text) stored,
  embedding vector(384) not null,
  metadata jsonb not null default '{}'::jsonb,
  user_id uuid references users(id) on delete cascade,
  disease_tag text,
  created_at timestamptz not null default now(),
  constraint rag_chunks_source_not_blank check (length(trim(source)) > 0),
  constraint rag_chunks_text_not_blank check (length(trim(chunk_text)) > 0)
);

drop trigger if exists set_users_updated_at on users;
create trigger set_users_updated_at
before update on users
for each row execute function set_updated_at();

drop trigger if exists set_health_profiles_updated_at on health_profiles;
create trigger set_health_profiles_updated_at
before update on health_profiles
for each row execute function set_updated_at();

drop trigger if exists set_chat_sessions_updated_at on chat_sessions;
create trigger set_chat_sessions_updated_at
before update on chat_sessions
for each row execute function set_updated_at();

create index if not exists idx_chat_sessions_user_created_at on chat_sessions(user_id, created_at desc);
create index if not exists idx_chat_messages_session_created_at on chat_messages(session_id, created_at);
create index if not exists idx_chat_messages_metadata_gin on chat_messages using gin(metadata);
do $$
begin
  create index if not exists idx_chat_messages_embedding_hnsw
  on chat_messages using hnsw (embedding vector_cosine_ops);
exception
  when undefined_object or feature_not_supported then null;
end $$;
create index if not exists idx_chat_sessions_parsed_nutrition_json_gin on chat_sessions using gin(parsed_nutrition_json);
create index if not exists idx_rag_chunks_source on rag_chunks(source);
create index if not exists idx_rag_chunks_source_type on rag_chunks(source_type);
create index if not exists idx_rag_chunks_disease_tag on rag_chunks(disease_tag);
create index if not exists idx_rag_chunks_user_id on rag_chunks(user_id);
create index if not exists idx_rag_chunks_metadata_gin on rag_chunks using gin(metadata);
do $$
begin
  create index if not exists idx_rag_chunks_embedding_hnsw
  on rag_chunks using hnsw (embedding vector_cosine_ops);
exception
  when undefined_object or feature_not_supported then null;
end $$;

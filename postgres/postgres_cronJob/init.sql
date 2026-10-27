CREATE EXTENSION IF NOT EXISTS pg_cron;

CREATE TABLE IF NOT EXISTS public.cron_job_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_name TEXT NOT NULL,
    ran_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION public.record_cron_job_run(p_job_name TEXT)
RETURNS VOID
LANGUAGE SQL
AS $function$
    INSERT INTO public.cron_job_runs (job_name) VALUES (p_job_name);
$function$;

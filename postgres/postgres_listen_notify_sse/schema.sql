CREATE TABLE IF NOT EXISTS jobs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title TEXT NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.event_outbox (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_type TEXT NOT NULL CHECK (event_type IN ('job_created')),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION notify_job_created()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $function$
DECLARE
    new_event_id BIGINT;
BEGIN
    PERFORM pg_advisory_xact_lock(1848, 1);

    INSERT INTO public.event_outbox (event_type, payload)
    VALUES (
        'job_created',
        jsonb_build_object(
            'id', NEW.id,
            'title', NEW.title,
            'created_at', NEW.created_at
        )
    )
    RETURNING event_id INTO new_event_id;

    PERFORM pg_notify(
        'job_events',
        new_event_id::text
    );
    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS jobs_created_trigger ON jobs;
CREATE TRIGGER jobs_created_trigger
AFTER INSERT ON jobs
FOR EACH ROW
EXECUTE FUNCTION notify_job_created();

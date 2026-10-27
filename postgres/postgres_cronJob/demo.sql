SELECT cron.schedule(
    'lesson-heartbeat',
    '* * * * *',
    $$SELECT public.record_cron_job_run('lesson-heartbeat');$$
);

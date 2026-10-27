SELECT jobid, jobname, schedule, command, nodename, nodeport, database, username, active
FROM cron.job
ORDER BY jobid;

SELECT run_id, job_name, ran_at
FROM public.cron_job_runs
ORDER BY ran_at DESC
LIMIT 20;

SELECT jobid, runid, status, return_message, start_time, end_time
FROM cron.job_run_details
ORDER BY start_time DESC
LIMIT 20;

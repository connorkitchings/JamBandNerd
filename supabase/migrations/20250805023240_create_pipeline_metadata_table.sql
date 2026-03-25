CREATE TABLE public.pipeline_metadata (
    pipeline_name TEXT PRIMARY KEY,
    last_updated TIMESTAMPTZ NOT NULL
);

ALTER TABLE public.pipeline_metadata ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public access"
ON public.pipeline_metadata
FOR ALL
USING (true)
WITH CHECK (true);;

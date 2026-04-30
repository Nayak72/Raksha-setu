-- ─────────────────────────────────────────────
-- Migration 002: Agent Logs
-- ─────────────────────────────────────────────

-- Table: agent_logs
-- Stores the step-by-step reasoning and outputs of the multi-agent system.
CREATE TABLE IF NOT EXISTS public.agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id UUID NOT NULL REFERENCES public.zones(id) ON DELETE CASCADE,
    agent_name VARCHAR(255) NOT NULL,
    decision TEXT,
    reasoning_steps JSONB DEFAULT '[]'::jsonb,
    tools_used JSONB DEFAULT '[]'::jsonb,
    confidence NUMERIC(5, 2) DEFAULT 0.0,
    routing_decision VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexing for real-time frontend queries
CREATE INDEX IF NOT EXISTS idx_agent_logs_zone_id ON public.agent_logs(zone_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_timestamp ON public.agent_logs(timestamp DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.agent_logs ENABLE ROW LEVEL SECURITY;

-- Allow anonymous read access (for public dashboard if needed)
CREATE POLICY "Allow public read access on agent_logs"
    ON public.agent_logs
    FOR SELECT
    USING (true);

-- Allow authenticated users / service role full access
CREATE POLICY "Allow service role all access on agent_logs"
    ON public.agent_logs
    FOR ALL
    USING (true);

-- Enable Realtime for the new table
ALTER PUBLICATION supabase_realtime ADD TABLE public.agent_logs;

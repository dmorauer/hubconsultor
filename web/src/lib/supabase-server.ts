import "server-only";
import { createClient } from "@supabase/supabase-js";

// Server-only client using the secret key. RLS on process_* tables has no policies,
// so only this key (service_role, bypasses RLS) can read/write them — the browser
// (publishable key) never touches this data directly.
export const supabaseServer = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SECRET_KEY!,
  { auth: { persistSession: false } }
);

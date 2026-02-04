// lib/supabase.ts
import { createClient } from '@supabase/supabase-js'
import { Database } from './types'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient<Database>(supabaseUrl, supabaseAnonKey)

// Helper function to get public URL for images
export const getImageUrl = (path: string) => {
  const { data } = supabase.storage.from('cat-photos').getPublicUrl(path)
  return data.publicUrl
}
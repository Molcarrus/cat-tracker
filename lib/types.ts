// lib/types.ts
export interface Cat {
  id: string
  name: string
  description: string | null
  color: string | null
  distinctive_features: string | null
  first_seen: string
  created_at: string
}

export interface Sighting {
  id: string
  cat_id: string
  seen_date: string
  seen_time: string
  location: string | null
  notes: string | null
  created_at: string
  cat?: Cat
}

export interface CatImage {
  id: string
  cat_id: string
  sighting_id: string | null
  image_url: string
  caption: string | null
  taken_at: string
  created_at: string
}

export interface CatWithDetails extends Cat {
  images: CatImage[]
  sightings: Sighting[]
  sighting_count: number
  last_seen: string | null
}

export interface Database {
  public: {
    Tables: {
      cats: {
        Row: Cat
        Insert: Omit<Cat, 'id' | 'created_at'>
        Update: Partial<Omit<Cat, 'id' | 'created_at'>>
      }
      sightings: {
        Row: Sighting
        Insert: Omit<Sighting, 'id' | 'created_at'>
        Update: Partial<Omit<Sighting, 'id' | 'created_at'>>
      }
      cat_images: {
        Row: CatImage
        Insert: Omit<CatImage, 'id' | 'created_at'>
        Update: Partial<Omit<CatImage, 'id' | 'created_at'>>
      }
    }
  }
}
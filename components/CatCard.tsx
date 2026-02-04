// components/CatCard.tsx
'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { supabase } from '@/lib/supabase'
import { Cat, CatImage } from '@/lib/types'
import { Camera, Calendar } from 'lucide-react'
import { format } from 'date-fns'

interface CatCardProps {
  cat: Cat
}

export default function CatCard({ cat }: CatCardProps) {
  const [image, setImage] = useState<CatImage | null>(null)
  const [sightingCount, setSightingCount] = useState(0)

  useEffect(() => {
    const fetchExtras = async () => {
      // Get first image
      const { data: imageData } = await supabase
        .from('cat_images')
        .select('*')
        .eq('cat_id', cat.id)
        .order('created_at', { ascending: false })
        .limit(1)
        .single()

      // Get sighting count
      const { count } = await supabase
        .from('sightings')
        .select('*', { count: 'exact', head: true })
        .eq('cat_id', cat.id)

      if (imageData) setImage(imageData)
      if (count !== null) setSightingCount(count)
    }
    fetchExtras()
  }, [cat.id])

  return (
    <Link href={`/cats/${cat.id}`}>
      <div className="card hover:shadow-lg transition-shadow cursor-pointer">
        <div className="h-48 bg-gray-100">
          {image ? (
            <img
              src={image.image_url}
              alt={cat.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-6xl">
              🐱
            </div>
          )}
        </div>
        <div className="p-4">
          <h3 className="text-xl font-bold text-gray-900">{cat.name}</h3>
          {cat.color && (
            <p className="text-gray-600">🎨 {cat.color}</p>
          )}
          {cat.description && (
            <p className="text-gray-500 text-sm mt-1 line-clamp-2">
              {cat.description}
            </p>
          )}
          <div className="flex items-center gap-4 mt-3 text-sm text-gray-400">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              {sightingCount} sightings
            </span>
          </div>
        </div>
      </div>
    </Link>
  )
}
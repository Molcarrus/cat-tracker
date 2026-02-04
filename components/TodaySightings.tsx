// components/TodaySightings.tsx
'use client'

import Link from 'next/link'
import { Sighting, Cat } from '@/lib/types'
import { MapPin, Clock } from 'lucide-react'
import { format } from 'date-fns'

interface TodaySightingsProps {
  sightings: (Sighting & { cat: Cat })[]
  onRefresh: () => void
}

export default function TodaySightings({ sightings }: TodaySightingsProps) {
  if (sightings.length === 0) {
    return (
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          📅 Today's Sightings
        </h2>
        <div className="card p-8 text-center">
          <p className="text-gray-500">No cats spotted today yet!</p>
          <p className="text-gray-400 text-sm mt-1">
            Log a sighting when you see a furry friend 🐱
          </p>
        </div>
      </section>
    )
  }

  return (
    <section>
      <h2 className="text-2xl font-bold text-gray-900 mb-4">
        📅 Today's Sightings ({sightings.length})
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {sightings.map((sighting) => (
          <Link key={sighting.id} href={`/cats/${sighting.cat_id}`}>
            <div className="card p-4 hover:shadow-lg transition-shadow cursor-pointer">
              <div className="flex items-center space-x-3">
                <div className="text-3xl">🐱</div>
                <div>
                  <h3 className="font-bold text-gray-900">{sighting.cat.name}</h3>
                  <div className="flex items-center gap-3 text-sm text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {sighting.seen_time?.slice(0, 5)}
                    </span>
                    {sighting.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {sighting.location}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              {sighting.notes && (
                <p className="text-gray-600 text-sm mt-2 line-clamp-2">
                  {sighting.notes}
                </p>
              )}
            </div>
          </Link>
        ))}
      </div>
    </section>
  )
}
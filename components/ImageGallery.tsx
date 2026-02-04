// components/ImageGallery.tsx
'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'
import { CatImage } from '@/lib/types'
import { X, Trash2, ChevronLeft, ChevronRight } from 'lucide-react'
import { format } from 'date-fns'

interface ImageGalleryProps {
  images: CatImage[]
  onDelete: () => void
}

export default function ImageGallery({ images, onDelete }: ImageGalleryProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  const handleDelete = async (imageId: string) => {
    if (confirm('Delete this photo?')) {
      await supabase.from('cat_images').delete().eq('id', imageId)
      onDelete()
      setSelectedIndex(null)
    }
  }

  const goToPrevious = () => {
    if (selectedIndex !== null && selectedIndex > 0) {
      setSelectedIndex(selectedIndex - 1)
    }
  }

  const goToNext = () => {
    if (selectedIndex !== null && selectedIndex < images.length - 1) {
      setSelectedIndex(selectedIndex + 1)
    }
  }

  if (images.length === 0) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500">No photos yet!</p>
        <p className="text-gray-400 text-sm mt-1">
          Upload a photo to start the gallery 📸
        </p>
      </div>
    )
  }

  return (
    <>
      {/* Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {images.map((image, index) => (
          <div
            key={image.id}
            className="card aspect-square cursor-pointer group relative overflow-hidden"
            onClick={() => setSelectedIndex(index)}
          >
            <img
              src={image.image_url}
              alt="Cat"
              className="w-full h-full object-cover group-hover:scale-105 transition-transform"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/50 to-transparent p-2">
              <p className="text-white text-xs">
                {format(new Date(image.taken_at), 'MMM d, yyyy')}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {selectedIndex !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center">
          <button
            onClick={() => setSelectedIndex(null)}
            className="absolute top-4 right-4 text-white hover:text-gray-300"
          >
            <X className="w-8 h-8" />
          </button>

          <button
            onClick={() => handleDelete(images[selectedIndex].id)}
            className="absolute top-4 left-4 text-white hover:text-red-400"
          >
            <Trash2 className="w-6 h-6" />
          </button>

          {selectedIndex > 0 && (
            <button
              onClick={goToPrevious}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-white hover:text-gray-300"
            >
              <ChevronLeft className="w-10 h-10" />
            </button>
          )}

          {selectedIndex < images.length - 1 && (
            <button
              onClick={goToNext}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-white hover:text-gray-300"
            >
              <ChevronRight className="w-10 h-10" />
            </button>
          )}

          <img
            src={images[selectedIndex].image_url}
            alt="Cat"
            className="max-w-full max-h-[85vh] object-contain"
          />

          <div className="absolute bottom-4 text-white text-center">
            <p>{format(new Date(images[selectedIndex].taken_at), 'MMMM d, yyyy')}</p>
            <p className="text-sm text-gray-400">
              {selectedIndex + 1} of {images.length}
            </p>
          </div>
        </div>
      )}
    </>
  )
}
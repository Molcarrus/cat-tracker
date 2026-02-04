// components/LogSightingModal.tsx
'use client'

import { useState, useRef } from 'react'
import { supabase, getImageUrl } from '@/lib/supabase'
import { Cat } from '@/lib/types'
import { X, Camera } from 'lucide-react'
import { format } from 'date-fns'

interface LogSightingModalProps {
  cats: Cat[]
  onClose: () => void
  onSuccess: () => void
}

export default function LogSightingModal({ cats, onClose, onSuccess }: LogSightingModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const [form, setForm] = useState({
    cat_id: '',
    seen_date: format(new Date(), 'yyyy-MM-dd'),
    seen_time: format(new Date(), 'HH:mm'),
    location: '',
    notes: '',
  })

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedImage(file)
      const reader = new FileReader()
      reader.onloadend = () => {
        setImagePreview(reader.result as string)
      }
      reader.readAsDataURL(file)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.cat_id) return

    setLoading(true)

    // Create sighting
    const { data: sighting, error: sightingError } = await supabase
      .from('sightings')
      .insert({
        cat_id: form.cat_id,
        seen_date: form.seen_date,
        seen_time: form.seen_time,
        location: form.location || null,
        notes: form.notes || null,
      })
      .select()
      .single()

    if (sightingError) {
      setLoading(false)
      return
    }

    // Upload image if selected
    if (selectedImage && sighting) {
      const fileExt = selectedImage.name.split('.').pop()
      const fileName = `${form.cat_id}/${Date.now()}.${fileExt}`

      const { error: uploadError } = await supabase.storage
        .from('cat-photos')
        .upload(fileName, selectedImage)

      if (!uploadError) {
        const imageUrl = getImageUrl(fileName)
        await supabase.from('cat_images').insert({
          cat_id: form.cat_id,
          sighting_id: sighting.id,
          image_url: imageUrl,
          taken_at: form.seen_date,
        })
      }
    }

    setLoading(false)
    onSuccess()
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Log Sighting 📍</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Which cat? *
            </label>
            <select
              value={form.cat_id}
              onChange={(e) => setForm({ ...form, cat_id: e.target.value })}
              className="input"
              required
            >
              <option value="">Select a cat...</option>
              {cats.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name} {cat.color && `(${cat.color})`}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Date
              </label>
              <input
                type="date"
                value={form.seen_date}
                onChange={(e) => setForm({ ...form, seen_date: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Time
              </label>
              <input
                type="time"
                value={form.seen_time}
                onChange={(e) => setForm({ ...form, seen_time: e.target.value })}
                className="input"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Location in park
            </label>
            <input
              type="text"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              className="input"
              placeholder="e.g., Near the fountain, Under the big oak tree"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Notes
            </label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              className="input"
              rows={2}
              placeholder="e.g., Was sleeping, Seemed hungry"
            />
          </div>

          {/* Image Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Add Photo (optional)
            </label>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleImageSelect}
              accept="image/*"
              className="hidden"
            />
            
            {imagePreview ? (
              <div className="relative">
                <img
                  src={imagePreview}
                  alt="Preview"
                  className="w-full h-48 object-cover rounded-lg"
                />
                <button
                  type="button"
                  onClick={() => {
                    setSelectedImage(null)
                    setImagePreview(null)
                  }}
                  className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full h-32 border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center text-gray-500 hover:border-primary-500 hover:text-primary-500 transition-colors"
              >
                <Camera className="w-8 h-8 mb-2" />
                <span>Click to add photo</span>
              </button>
            )}
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !form.cat_id}
              className="btn-primary flex-1"
            >
              {loading ? 'Saving...' : 'Log Sighting'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
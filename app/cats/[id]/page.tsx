// app/cats/[id]/page.tsx
'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { supabase, getImageUrl } from '@/lib/supabase'
import { Cat, Sighting, CatImage } from '@/lib/types'
import ImageGallery from '@/components/ImageGallery'
import { ArrowLeft, Calendar, Camera, MapPin, Edit2, Trash2, Upload } from 'lucide-react'
import { format } from 'date-fns'

export default function CatDetailPage() {
  const params = useParams()
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  const [cat, setCat] = useState<Cat | null>(null)
  const [sightings, setSightings] = useState<Sighting[]>([])
  const [images, setImages] = useState<CatImage[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    color: '',
    distinctive_features: '',
  })

  const fetchCatDetails = async () => {
    const catId = params.id as string

    // Fetch cat
    const { data: catData } = await supabase
      .from('cats')
      .select('*')
      .eq('id', catId)
      .single()

    // Fetch sightings
    const { data: sightingsData } = await supabase
      .from('sightings')
      .select('*')
      .eq('cat_id', catId)
      .order('seen_date', { ascending: false })

    // Fetch images
    const { data: imagesData } = await supabase
      .from('cat_images')
      .select('*')
      .eq('cat_id', catId)
      .order('taken_at', { ascending: false })

    if (catData) {
      setCat(catData)
      setEditForm({
        name: catData.name,
        description: catData.description || '',
        color: catData.color || '',
        distinctive_features: catData.distinctive_features || '',
      })
    }
    if (sightingsData) setSightings(sightingsData)
    if (imagesData) setImages(imagesData)
    setLoading(false)
  }

  useEffect(() => {
    fetchCatDetails()
  }, [params.id])

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !cat) return

    setUploading(true)
    
    const fileExt = file.name.split('.').pop()
    const fileName = `${cat.id}/${Date.now()}.${fileExt}`

    // Upload to Supabase Storage
    const { error: uploadError } = await supabase.storage
      .from('cat-photos')
      .upload(fileName, file)

    if (uploadError) {
      console.error('Upload error:', uploadError)
      setUploading(false)
      return
    }

    // Get public URL
    const imageUrl = getImageUrl(fileName)

    // Save to database
    await supabase.from('cat_images').insert({
      cat_id: cat.id,
      image_url: imageUrl,
      taken_at: format(new Date(), 'yyyy-MM-dd'),
    })

    await fetchCatDetails()
    setUploading(false)
  }

  const handleUpdate = async () => {
    if (!cat) return

    await supabase
      .from('cats')
      .update(editForm)
      .eq('id', cat.id)

    setIsEditing(false)
    fetchCatDetails()
  }

  const handleDelete = async () => {
    if (!cat) return
    
    if (confirm(`Are you sure you want to delete ${cat.name}? This will also delete all their photos and sightings.`)) {
      await supabase.from('cats').delete().eq('id', cat.id)
      router.push('/')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  if (!cat) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Cat not found</p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Back Button */}
      <button
        onClick={() => router.back()}
        className="flex items-center space-x-2 text-gray-600 hover:text-gray-900"
      >
        <ArrowLeft className="w-5 h-5" />
        <span>Back</span>
      </button>

      {/* Cat Header */}
      <div className="card p-6">
        <div className="flex flex-col md:flex-row gap-6">
          {/* Main Image */}
          <div className="w-full md:w-64 h-64 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
            {images.length > 0 ? (
              <img
                src={images[0].image_url}
                alt={cat.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-6xl">
                🐱
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1">
            {isEditing ? (
              <div className="space-y-4">
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  className="input text-2xl font-bold"
                />
                <input
                  type="text"
                  value={editForm.color}
                  onChange={(e) => setEditForm({ ...editForm, color: e.target.value })}
                  placeholder="Color"
                  className="input"
                />
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  placeholder="Description"
                  className="input"
                  rows={2}
                />
                <textarea
                  value={editForm.distinctive_features}
                  onChange={(e) => setEditForm({ ...editForm, distinctive_features: e.target.value })}
                  placeholder="Distinctive features"
                  className="input"
                  rows={2}
                />
                <div className="flex gap-2">
                  <button onClick={handleUpdate} className="btn-primary">Save</button>
                  <button onClick={() => setIsEditing(false)} className="btn-secondary">Cancel</button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex items-start justify-between">
                  <h1 className="text-3xl font-bold text-gray-900">{cat.name}</h1>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setIsEditing(true)}
                      className="p-2 text-gray-500 hover:text-primary-500"
                    >
                      <Edit2 className="w-5 h-5" />
                    </button>
                    <button
                      onClick={handleDelete}
                      className="p-2 text-gray-500 hover:text-red-500"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  </div>
                </div>
                
                {cat.color && (
                  <p className="text-lg text-gray-600 mt-1">🎨 {cat.color}</p>
                )}
                
                {cat.description && (
                  <p className="text-gray-700 mt-3">{cat.description}</p>
                )}
                
                {cat.distinctive_features && (
                  <p className="text-gray-600 mt-2">
                    <span className="font-medium">Distinctive features:</span> {cat.distinctive_features}
                  </p>
                )}

                <div className="flex flex-wrap gap-4 mt-4 text-sm text-gray-500">
                  <span className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    First seen: {format(new Date(cat.first_seen), 'MMM d, yyyy')}
                  </span>
                  <span className="flex items-center gap-1">
                    <Camera className="w-4 h-4" />
                    {images.length} photos
                  </span>
                  <span className="flex items-center gap-1">
                    <MapPin className="w-4 h-4" />
                    {sightings.length} sightings
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Upload Photo Button */}
      <div className="flex gap-4">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleImageUpload}
          accept="image/*"
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="btn-primary flex items-center space-x-2"
        >
          <Upload className="w-5 h-5" />
          <span>{uploading ? 'Uploading...' : 'Upload Photo'}</span>
        </button>
      </div>

      {/* Photo Gallery */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">📸 Photos</h2>
        <ImageGallery images={images} onDelete={fetchCatDetails} />
      </section>

      {/* Sightings History */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">📅 Sighting History</h2>
        {sightings.length === 0 ? (
          <p className="text-gray-500">No sightings recorded yet.</p>
        ) : (
          <div className="space-y-3">
            {sightings.map((sighting) => (
              <div key={sighting.id} className="card p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium">
                    {format(new Date(sighting.seen_date), 'EEEE, MMMM d, yyyy')}
                  </p>
                  <p className="text-sm text-gray-500">
                    at {sighting.seen_time?.slice(0, 5)}
                    {sighting.location && ` • ${sighting.location}`}
                  </p>
                  {sighting.notes && (
                    <p className="text-gray-600 mt-1">{sighting.notes}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
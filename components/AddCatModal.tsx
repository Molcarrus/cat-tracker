'use client'

import { useState } from 'react'
import { supabase } from '@/lib/supabase'
import { X } from 'lucide-react'

interface AddCatModalProps {
  onClose: () => void
  onSuccess: () => void
}

export default function AddCatModal({ onClose, onSuccess }: AddCatModalProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [color, setColor] = useState('')
  const [description, setDescription] = useState('')
  const [distinctiveFeatures, setDistinctiveFeatures] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    console.log('Form submitted!')
    console.log('Name:', name)
    
    if (!name.trim()) {
      setError('Please enter a name')
      return
    }

    setLoading(true)
    setError(null)

    try {
      console.log('Attempting to insert cat...')
      
      const { data, error: insertError } = await supabase
        .from('cats')
        .insert({
          name: name.trim(),
          color: color.trim() || null,
          description: description.trim() || null,
          distinctive_features: distinctiveFeatures.trim() || null,
        })
        .select()

      console.log('Insert response:', { data, insertError })

      if (insertError) {
        console.error('Supabase error:', insertError)
        setError(insertError.message)
        setLoading(false)
        return
      }

      console.log('Cat added successfully!')
      onSuccess()
      
    } catch (err) {
      console.error('Unexpected error:', err)
      setError('Something went wrong')
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-md w-full p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold">Add New Cat 🐱</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input"
              placeholder="e.g., Mr. Whiskers"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Color / Pattern
            </label>
            <input
              type="text"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="input"
              placeholder="e.g., Orange tabby"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input"
              rows={2}
              placeholder="e.g., Friendly, loves belly rubs"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Distinctive Features
            </label>
            <textarea
              value={distinctiveFeatures}
              onChange={(e) => setDistinctiveFeatures(e.target.value)}
              className="input"
              rows={2}
              placeholder="e.g., Notched ear, white spot on nose"
            />
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
              disabled={loading}
              className="btn-primary flex-1"
            >
              {loading ? 'Adding...' : 'Add Cat'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
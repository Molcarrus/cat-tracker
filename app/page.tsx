'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { Cat } from '@/lib/types'
import CatCard from '@/components/CatCard'
import AddCatModal from '@/components/AddCatModal'
import { Plus } from 'lucide-react'

export default function Home() {
  const [cats, setCats] = useState<Cat[]>([])
  const [showAddCat, setShowAddCat] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchCats = async () => {
    setLoading(true)
    const { data, error } = await supabase
      .from('cats')
      .select('*')
      .order('name')
    
    if (error) {
      console.error('Error fetching cats:', error)
    }
    
    if (data) {
      setCats(data)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchCats()
  }, [])

  const handleCatAdded = () => {
    setShowAddCat(false)
    fetchCats()
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          🐱 Park Cat Tracker
        </h1>
        <p className="text-gray-600">
          Keep track of all your furry friends at the park!
        </p>
      </div>

      {/* Add Cat Button - Always Visible */}
      <div className="flex justify-center">
        <button
          onClick={() => setShowAddCat(true)}
          className="btn-primary flex items-center space-x-2 text-lg px-6 py-3"
        >
          <Plus className="w-6 h-6" />
          <span>Add New Cat</span>
        </button>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
        </div>
      )}

      {/* All Cats */}
      {!loading && (
        <section>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">🐾 All Cats ({cats.length})</h2>
          
          {cats.length === 0 ? (
            <div className="card p-12 text-center">
              <div className="text-6xl mb-4">🐱</div>
              <p className="text-gray-500 text-lg">No cats added yet!</p>
              <p className="text-gray-400">Click the button above to add your first cat.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {cats.map((cat) => (
                <CatCard key={cat.id} cat={cat} />
              ))}
            </div>
          )}
        </section>
      )}

      {/* Add Cat Modal */}
      {showAddCat && (
        <AddCatModal 
          onClose={() => setShowAddCat(false)} 
          onSuccess={handleCatAdded} 
        />
      )}
    </div>
  )
}
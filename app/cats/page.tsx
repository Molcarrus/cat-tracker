// app/cats/page.tsx
'use client'

import { useState, useEffect } from 'react'
import { supabase } from '@/lib/supabase'
import { Cat } from '@/lib/types'
import CatCard from '@/components/CatCard'
import { Search } from 'lucide-react'

export default function CatsPage() {
  const [cats, setCats] = useState<Cat[]>([])
  const [filteredCats, setFilteredCats] = useState<Cat[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchCats = async () => {
      const { data } = await supabase
        .from('cats')
        .select('*')
        .order('name')
      
      if (data) {
        setCats(data)
        setFilteredCats(data)
      }
      setLoading(false)
    }
    fetchCats()
  }, [])

  useEffect(() => {
    const filtered = cats.filter(cat => 
      cat.name.toLowerCase().includes(search.toLowerCase()) ||
      cat.color?.toLowerCase().includes(search.toLowerCase()) ||
      cat.description?.toLowerCase().includes(search.toLowerCase())
    )
    setFilteredCats(filtered)
  }, [search, cats])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-gray-900">All Cats</h1>
      
      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          placeholder="Search cats by name, color..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input pl-10"
        />
      </div>

      {/* Cats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCats.map((cat) => (
          <CatCard key={cat.id} cat={cat} />
        ))}
      </div>

      {filteredCats.length === 0 && (
        <p className="text-center text-gray-500 py-12">
          No cats found matching "{search}"
        </p>
      )}
    </div>
  )
}
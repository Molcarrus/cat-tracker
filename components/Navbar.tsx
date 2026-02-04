// components/Navbar.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Cat, Calendar } from 'lucide-react'

export default function Navbar() {
  const pathname = usePathname()

  const links = [
    { href: '/', label: 'Home', icon: Home },
    { href: '/cats', label: 'All Cats', icon: Cat },
  ]

  return (
    <nav className="bg-white shadow-sm border-b border-gray-100">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center space-x-2">
            <span className="text-2xl">🐱</span>
            <span className="font-bold text-xl text-gray-900">Cat Tracker</span>
          </Link>

          <div className="flex items-center space-x-1">
            {links.map((link) => {
              const Icon = link.icon
              const isActive = pathname === link.href
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center space-x-1 px-4 py-2 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="hidden sm:inline">{link.label}</span>
                </Link>
              )
            })}
          </div>
        </div>
      </div>
    </nav>
  )
}
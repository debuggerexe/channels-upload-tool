"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { Video, Settings, Database, Upload, Sparkles } from "lucide-react"

const sidebarItems = [
  {
    title: "视频管理",
    href: "/",
    icon: Video,
    color: "from-teal-500 to-cyan-500",
  },
  {
    title: "配置管理",
    href: "/config",
    icon: Settings,
    color: "from-sky-500 to-blue-500",
  },
  {
    title: "Notion 集成",
    href: "/notion",
    icon: Database,
    color: "from-emerald-500 to-teal-500",
  },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="flex h-full w-72 flex-col border-r border-white/5 bg-[#0a0c10]/90 backdrop-blur-xl">
      {/* Logo Area */}
      <div className="flex h-20 items-center border-b border-white/5 px-6">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-teal-500/20 group-hover:shadow-teal-500/40 transition-all duration-300">
              <Upload className="h-5 w-5 text-white" />
            </div>
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-gradient-to-br from-sky-400 to-blue-500 rounded-full border-2 border-[#0a0c10]" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-lg text-slate-100 tracking-tight">视频号工具</span>
            <span className="text-xs text-slate-500 flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              Creator Studio
            </span>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-4">
        {sidebarItems.map((item, index) => {
          const isActive = pathname === item.href
          const Icon = item.icon
          
          return (
            <motion.div
              key={item.href}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all duration-300 group relative overflow-hidden",
                  isActive 
                    ? "bg-white/5 border border-white/10" 
                    : "hover:bg-white/5 border border-transparent"
                )}
              >
                {/* Active Indicator */}
                {isActive && (
                  <motion.div
                    layoutId="activeNav"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-gradient-to-b from-teal-400 to-cyan-500"
                  />
                )}
                
                {/* Icon Container */}
                <div className={cn(
                  "w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-300",
                  isActive 
                    ? `bg-gradient-to-br ${item.color} shadow-lg` 
                    : "bg-slate-800/50 group-hover:bg-slate-700/50"
                )}>
                  <Icon className={cn(
                    "w-4 h-4 transition-colors",
                    isActive ? "text-white" : "text-slate-400 group-hover:text-slate-300"
                  )} />
                </div>
                
                {/* Label */}
                <span className={cn(
                  "font-medium transition-colors",
                  isActive ? "text-slate-100" : "text-slate-400 group-hover:text-slate-300"
                )}>
                  {item.title}
                </span>

                {/* Active Glow */}
                {isActive && (
                  <div className="absolute inset-0 bg-gradient-to-r from-teal-500/10 to-transparent pointer-events-none" />
                )}
              </Link>
            </motion.div>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/5">
        <div className="glass rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-teal-500 status-dot" />
            <span className="text-sm text-slate-500">系统运行正常</span>
          </div>
          <div className="text-xs text-slate-600">
            微信视频号上传工具 v1.0
          </div>
        </div>
      </div>
    </div>
  )
}

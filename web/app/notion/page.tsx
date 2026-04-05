"use client"

import { motion } from "framer-motion"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  Database, Cloud, Info, Sparkles, Shield, Zap, 
  Globe, Lock, FileText, CheckCircle2
} from "lucide-react"

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: "easeOut" as const }
  }
}

export default function NotionPage() {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full p-8"
    >
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-4"
        >
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-teal-500/20 to-cyan-500/20 flex items-center justify-center border border-slate-700/50">
            <Database className="w-7 h-7 text-teal-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Notion 集成</h1>
            <p className="text-slate-500 mt-1">云端数据源配置指南</p>
          </div>
        </motion.div>

        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-6"
        >
          {/* Setup Guide Card */}
          <motion.div variants={itemVariants}>
            <Card className="glass border-0 shadow-lg border border-slate-700/50">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500/20 to-cyan-500/20 flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-teal-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-slate-100">快速开始</CardTitle>
                    <CardDescription className="text-slate-500">三步完成 Notion 云端集成</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 md:grid-cols-3">
                  {[
                    {
                      step: "1",
                      icon: FileText,
                      title: "创建数据库",
                      desc: "在 Notion 中创建视频管理数据库",
                      color: "from-teal-500/20 to-cyan-500/20",
                      iconColor: "text-teal-400"
                    },
                    {
                      step: "2",
                      icon: Shield,
                      title: "配置 Token",
                      desc: "获取 Notion API Token 并设置",
                      color: "from-cyan-500/20 to-sky-500/20",
                      iconColor: "text-cyan-400"
                    },
                    {
                      step: "3",
                      icon: Database,
                      title: "填写配置",
                      desc: "在配置管理页面填写数据库信息",
                      color: "from-sky-500/20 to-blue-500/20",
                      iconColor: "text-sky-400"
                    }
                  ].map((item, idx) => (
                    <motion.div 
                      key={idx}
                      whileHover={{ scale: 1.02 }}
                      className="glass rounded-xl p-4 border border-slate-700/50"
                    >
                      <div className="flex items-center gap-3 mb-3">
                        <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${item.color} flex items-center justify-center`}>
                          <item.icon className={`w-4 h-4 ${item.iconColor}`} />
                        </div>
                        <span className="text-sm font-medium text-slate-500">步骤 {item.step}</span>
                      </div>
                      <h4 className="font-semibold text-slate-100 mb-1">{item.title}</h4>
                      <p className="text-xs text-slate-500">{item.desc}</p>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Database Schema Card */}
          <motion.div variants={itemVariants}>
            <Card className="glass border-0 shadow-lg border border-slate-700/50">
              <CardHeader className="pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500/20 to-cyan-500/20 flex items-center justify-center">
                    <Info className="w-5 h-5 text-teal-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-slate-100">数据库字段说明</CardTitle>
                    <CardDescription className="text-slate-500">Notion 数据库需要包含以下字段</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 md:grid-cols-2">
                  {[
                    { name: "短标题", type: "Title", desc: "视频号短标题，用于匹配本地视频" },
                    { name: "标题", type: "Rich Text", desc: "视频主标题" },
                    { name: "描述", type: "Rich Text", desc: "视频描述内容" },
                    { name: "标签", type: "Rich Text", desc: "话题标签" },
                    { name: "合集", type: "Multi-select", desc: "视频合集" },
                    { name: "发布日期", type: "Date", desc: "发布日期" },
                  ].map((field, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-slate-800/50 border border-slate-700/50">
                      <CheckCircle2 className="w-5 h-5 text-teal-400 mt-0.5" />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-slate-100">{field.name}</span>
                          <Badge variant="outline" className="text-[10px] border-slate-600/50 text-slate-500">
                            {field.type}
                          </Badge>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">{field.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Benefits Grid */}
          <div className="grid gap-6 md:grid-cols-2">
            <motion.div variants={itemVariants}>
              <Card className="glass border-0 shadow-lg border border-slate-700/50 h-full">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500/20 to-cyan-500/20 flex items-center justify-center">
                      <Cloud className="w-5 h-5 text-teal-400" />
                    </div>
                    <CardTitle className="text-lg text-slate-100">云端优势</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {[
                      "多人协作编辑视频信息",
                      "随时随地管理发布计划",
                      "数据备份在云端",
                      "支持复杂筛选和排序"
                    ].map((item, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-sm text-slate-500">
                        <Zap className="w-4 h-4 text-teal-400" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div variants={itemVariants}>
              <Card className="glass border-0 shadow-lg border border-slate-700/50 h-full">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500/20 to-blue-500/20 flex items-center justify-center">
                      <Lock className="w-5 h-5 text-sky-400" />
                    </div>
                    <CardTitle className="text-lg text-slate-100">环境变量</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="rounded-lg bg-black/40 p-4 font-mono text-sm border border-slate-700/50">
                    <p className="text-slate-600"># 在 ~/.bashrc 或 ~/.zshrc 中添加</p>
                    <p className="mt-2 text-slate-400">export NOTION_API_TOKEN=&quot;<span className="text-teal-400">your_token_here</span>&quot;</p>
                  </div>
                  <p className="text-xs text-slate-500">
                    <Globe className="w-3 h-3 inline mr-1" />
                    获取 Token: 访问 <a href="https://www.notion.so/my-integrations" target="_blank" rel="noopener noreferrer" className="text-teal-400 hover:underline">Notion Integrations</a>
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Status */}
          <motion.div 
            variants={itemVariants}
            className="flex items-center gap-3 glass rounded-xl p-4 border border-slate-700/50"
          >
            <div className="w-2 h-2 rounded-full bg-amber-400 status-dot" />
            <span className="text-sm text-slate-500">
              请确保已设置 <code className="bg-slate-800/50 px-1.5 py-0.5 rounded text-slate-400">NOTION_API_TOKEN</code> 环境变量，并在配置管理中填写数据库信息
            </span>
          </motion.div>
        </motion.div>
      </div>
    </motion.div>
  )
}

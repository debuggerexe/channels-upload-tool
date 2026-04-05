"use client"

import { useEffect, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { getConfig, updateConfig, resetConfig } from "@/lib/api"
import { 
  Save, RotateCcw, CheckCircle, TestTube, Settings2, Clock, 
  Video, Image, Folder, Database, Sparkles, Zap, Globe, Shield
} from "lucide-react"

export default function ConfigPage() {
  const [config, setConfig] = useState({
    publish_date: "",
    publish_times: "",
    timezone: "",
    video_dir: "",
    text_dir: "",
    original_declaration: true,
    cover_position: "",
    collection: "",
    notion_api_token: "",
    notion_database_id: "",
    notion_database_name: "",
  })
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)
  const [testingNotion, setTestingNotion] = useState(false)
  const [testResult, setTestResult] = useState<{success: boolean; message: string} | null>(null)

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1, delayChildren: 0.1 }
    }
  }

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5, ease: "easeOut" as const }
    }
  }

  const headerVariants = {
    hidden: { opacity: 0, y: -20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.6, ease: "easeOut" as const }
    }
  }

  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    try {
      const data = await getConfig()
      setConfig({
        publish_date: data.publish_date || "",
        publish_times: Array.isArray(data.publish_times) ? data.publish_times.join(", ") : data.publish_times || "",
        timezone: data.timezone || "",
        video_dir: data.video_dir || "",
        text_dir: data.text_dir || "",
        original_declaration: data.original_declaration ?? true,
        cover_position: data.cover_position || "middle",
        collection: data.collection || "",
        notion_api_token: data.notion_api_token || "",
        notion_database_id: data.notion_database_id || "",
        notion_database_name: data.notion_database_name || "",
      })
    } catch (error) {
      console.error("获取配置失败:", error)
    }
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const configToSave = {
        ...config,
        publish_times: config.publish_times.split(",").map((t: string) => t.trim()).filter(Boolean),
        original_declaration: config.original_declaration,
      }
      await updateConfig(configToSave)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (error) {
      console.error("保存配置失败:", error)
      alert("保存配置失败")
    }
    setLoading(false)
  }

  const handleReset = async () => {
    if (!confirm("确定要重置为默认配置吗？")) return
    setLoading(true)
    try {
      await resetConfig()
      await fetchConfig()
      alert("配置已重置")
    } catch (error) {
      console.error("重置配置失败:", error)
    }
    setLoading(false)
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full p-8"
    >
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <motion.div 
          variants={headerVariants}
          initial="hidden"
          animate="visible"
          className="glass rounded-2xl p-6"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-teal-500/20 to-cyan-500/20 flex items-center justify-center border border-slate-700/50">
                <Settings2 className="w-7 h-7 text-teal-400" />
              </div>
              <div>
                <h1 className="text-3xl font-bold gradient-text">配置管理</h1>
                <p className="text-slate-500 mt-1">管理上传任务的配置参数</p>
              </div>
            </div>
            <div className="flex gap-3">
              <AnimatePresence>
                {saved && (
                  <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                  >
                    <Badge className="bg-teal-500/20 text-teal-400 border-teal-500/30 backdrop-blur-sm px-4 py-2">
                      <CheckCircle className="w-4 h-4 mr-2" />
                      已保存
                    </Badge>
                  </motion.div>
                )}
              </AnimatePresence>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button 
                  variant="outline" 
                  onClick={handleReset} 
                  disabled={loading}
                  className="gap-2 bg-slate-800/50 backdrop-blur-sm hover:bg-slate-700/50 border-slate-700/50 text-slate-400 hover:text-slate-200"
                >
                  <RotateCcw className="w-4 h-4" />
                  重置
                </Button>
              </motion.div>
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button 
                  onClick={handleSave} 
                  disabled={loading}
                  className="gap-2 bg-gradient-to-r from-teal-500 to-cyan-500 hover:from-teal-600 hover:to-cyan-600 shadow-lg shadow-teal-500/25 border-0"
                >
                  <Save className="w-4 h-4" />
                  保存配置
                </Button>
              </motion.div>
            </div>
          </div>
        </motion.div>

        {/* Config Cards */}
        <motion.div 
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid gap-6 md:grid-cols-2"
        >
          {/* 发布设置 */}
          <motion.div variants={cardVariants}>
            <Card className="glass border-0 shadow-lg overflow-hidden group card-hover border border-slate-700/50">
              <CardHeader className="bg-gradient-to-r from-teal-500/10 to-cyan-500/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-teal-500/20 flex items-center justify-center">
                    <Clock className="w-5 h-5 text-teal-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-slate-100">发布设置</CardTitle>
                    <CardDescription className="text-slate-500">配置视频发布的日期和时间</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-5 pt-5">
                <div className="space-y-2">
                  <Label htmlFor="publish_date" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
                    发布日期
                  </Label>
                  <Input
                    id="publish_date"
                    type="date"
                    value={config.publish_date}
                    onChange={(e) => setConfig({ ...config, publish_date: e.target.value })}
                    className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50"
                  />
                  <p className="text-xs text-slate-600">格式: YYYY-MM-DD</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="publish_times" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                    发布时间
                  </Label>
                  <Input
                    id="publish_times"
                    placeholder="10:00, 14:00, 18:00"
                    value={config.publish_times}
                    onChange={(e) => setConfig({ ...config, publish_times: e.target.value })}
                    className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50"
                  />
                  <p className="text-xs text-slate-600">多个时间用逗号分隔</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="timezone" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                    时区
                  </Label>
                  <Input
                    id="timezone"
                    value={config.timezone}
                    onChange={(e) => setConfig({ ...config, timezone: e.target.value })}
                    className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50"
                  />
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* 视频设置 */}
          <motion.div variants={cardVariants}>
            <Card className="glass border-0 shadow-lg overflow-hidden group card-hover border border-slate-700/50">
              <CardHeader className="bg-gradient-to-r from-sky-500/10 to-blue-500/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-sky-500/20 flex items-center justify-center">
                    <Video className="w-5 h-5 text-sky-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-slate-100">视频设置</CardTitle>
                    <CardDescription className="text-slate-500">配置视频文件夹和封面处理</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-5 pt-5">
                <div className="space-y-2">
                  <Label htmlFor="video_dir" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <Folder className="w-3.5 h-3.5 text-sky-400" />
                    视频文件夹
                  </Label>
                  <Input
                    id="video_dir"
                    value={config.video_dir}
                    onChange={(e) => setConfig({ ...config, video_dir: e.target.value })}
                    className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="cover_position" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <Image className="w-3.5 h-3.5 text-cyan-400" />
                    封面裁剪位置
                  </Label>
                  <Select
                    value={config.cover_position}
                    onValueChange={(value) => setConfig({ ...config, cover_position: value })}
                  >
                    <SelectTrigger className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50">
                      <SelectValue placeholder="选择裁剪位置" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="top">顶部</SelectItem>
                      <SelectItem value="middle">中间</SelectItem>
                      <SelectItem value="bottom">底部</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="original_declaration" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <Shield className="w-3.5 h-3.5 text-amber-400" />
                    原创声明
                  </Label>
                  <Select
                    value={config.original_declaration ? "true" : "false"}
                    onValueChange={(value) => setConfig({ ...config, original_declaration: value === "true" })}
                  >
                    <SelectTrigger className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50">
                      <SelectValue placeholder="是否声明原创" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="true">是</SelectItem>
                      <SelectItem value="false">否</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* 合集设置 */}
          <motion.div variants={cardVariants}>
            <Card className="glass border-0 shadow-lg overflow-hidden group card-hover border border-slate-700/50">
              <CardHeader className="bg-gradient-to-r from-amber-500/10 to-orange-500/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-slate-100">合集设置</CardTitle>
                    <CardDescription className="text-slate-500">配置默认视频合集</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-5 pt-5">
                <div className="space-y-2">
                  <Label htmlFor="collection" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    默认合集
                  </Label>
                  <Input
                    id="collection"
                    value={config.collection}
                    onChange={(e) => setConfig({ ...config, collection: e.target.value })}
                    placeholder="合集名称"
                    className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50"
                  />
                  <p className="text-xs text-slate-600">支持多个合集，用逗号分隔</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Notion 设置 */}
          <motion.div variants={cardVariants}>
            <Card className="glass border-0 shadow-lg overflow-hidden group card-hover border border-slate-700/50">
              <CardHeader className="bg-gradient-to-r from-cyan-500/10 to-sky-500/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                    <Database className="w-5 h-5 text-cyan-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-slate-100">Notion 设置</CardTitle>
                    <CardDescription className="text-slate-500">配置 Notion 云端数据源</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-5 pt-5">
                <div className="space-y-2">
                  <Label htmlFor="notion_api_token" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <Zap className="w-3.5 h-3.5 text-cyan-400" />
                    API Token
                  </Label>
                  <Input
                    id="notion_api_token"
                    type="password"
                    value={config.notion_api_token}
                    onChange={(e) => setConfig({ ...config, notion_api_token: e.target.value })}
                    placeholder="secret_xxxxxxxxxxxxxxxxxxxxxxxx"
                    className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50"
                  />
                  <p className="text-xs text-slate-600">在 Notion 集成设置中创建</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notion_database_id" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <Globe className="w-3.5 h-3.5 text-sky-400" />
                    数据库 ID
                  </Label>
                  <Input
                    id="notion_database_id"
                    value={config.notion_database_id}
                    onChange={(e) => setConfig({ ...config, notion_database_id: e.target.value })}
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="notion_database_name" className="text-sm font-medium flex items-center gap-2 text-slate-300">
                    <Database className="w-3.5 h-3.5 text-cyan-400" />
                    数据库名称
                  </Label>
                  <Input
                    id="notion_database_name"
                    value={config.notion_database_name}
                    onChange={(e) => setConfig({ ...config, notion_database_name: e.target.value })}
                    placeholder="Database1"
                    className="bg-slate-800/50 border-slate-700/50 text-slate-200 focus:border-teal-500/50"
                  />
                </div>

                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button
                    variant="outline"
                    className="w-full gap-2 bg-slate-800/50 backdrop-blur-sm hover:bg-slate-700/50 border-slate-700/50 text-slate-400 hover:text-slate-200"
                    disabled={testingNotion || !config.notion_api_token}
                    onClick={async () => {
                      setTestingNotion(true)
                      setTestResult(null)
                      try {
                        const res = await fetch('http://localhost:8000/api/config/test_notion', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({ 
                            notion_api_token: config.notion_api_token,
                            notion_database_id: config.notion_database_id,
                            notion_database_name: config.notion_database_name
                          })
                        })
                        const data = await res.json()
                        setTestResult(data)
                      } catch (e) {
                        setTestResult({ success: false, message: '测试失败' })
                      }
                      setTestingNotion(false)
                    }}
                  >
                    <TestTube className="w-4 h-4" />
                    {testingNotion ? '测试中...' : '测试连接'}
                  </Button>
                </motion.div>

                <AnimatePresence>
                  {testResult && (
                    <motion.div
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                    >
                      <Badge 
                        variant={testResult.success ? "default" : "destructive"} 
                        className={`w-full justify-center py-2 ${testResult.success ? "bg-teal-500/20 text-teal-400 border-teal-500/30" : ""}`}
                      >
                        {testResult.success ? <CheckCircle className="w-4 h-4 mr-1" /> : null}
                        {testResult.message}
                      </Badge>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </motion.div>
  )
}

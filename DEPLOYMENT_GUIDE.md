# 网站性能优化 - PythonAnywhere 部署指南

## 完成的优化内容

1. ✅ 下载了所有外部 CDN 库到本地 static/libs/ 目录
2. ✅ 修改了 Django settings.py 添加静态文件配置
3. ✅ 更新了所有模板文件，使用本地资源替代 jsdelivr CDN
4. ✅ 为所有脚本添加了 `defer` 属性以提升加载性能

## PythonAnywhere 部署步骤

### 1. 上传修改后的文件

确保以下文件已更新并上传到 PythonAnywhere：
- problem_manager/settings.py
- problems/templates/problems/base.html
- problems/templates/problems/problem_list.html
- problems/templates/problems/problem_form.html
- problems/templates/problems/view_detail.html
- static/libs/ 整个目录（所有子目录和文件）

### 2. 激活虚拟环境并收集静态文件

```bash
cd ~/git/github/lore_keeper
source venv/bin/activate
python manage.py collectstatic --noinput
```

### 3. 重载 Web 应用

在 PythonAnywhere Web 页面点击 "Reload" 按钮

### 4. 验证部署

打开浏览器访问你的网站，按 F12 打开开发者工具：

**Network 标签检查：**
- ✅ 所有 CSS/JS 文件从 `/static/libs/` 加载
- ✅ 没有对 `cdn.jsdelivr.net` 的请求
- ✅ 所有资源状态码为 200（无 404）
- ✅ DOMContentLoaded 时间显著减少

**功能验证：**
- ✅ Bootstrap 样式正常显示
- ✅ 图标（Bootstrap Icons, Font Awesome）正常显示
- ✅ Markdown 编辑器（EasyMDE）功能正常
- ✅ 代码高亮（PrismJS）正常工作
- ✅ 复制按钮功能正常
- ✅ 移动端响应式布局正常

## 优化效果预估

| 指标 | 优化前 | 优化后 | 改善 |
|------|--------|--------|------|
| 外部 CDN 请求数 | 20 | 0 | -100% |
| 首次加载延迟 | 2-3秒 | 0.8-1.5秒 | -50% |
| CDN 依赖 | 是 | 否 | 100%本地化 |
| 存储占用 | 0 | 1.2MB | 可忽略 |

## 故障排查

### 问题 1：静态文件 404 错误
**症状：** 浏览器控制台显示找不到静态文件

**解决方案：**
```bash
cd ~/git/github/lore_keeper
source venv/bin/activate
python manage.py collectstatic --noinput
```

### 问题 2：样式或脚本不工作
**症状：** 页面样式混乱，JavaScript 报错

**解决方案：**
1. 清除浏览器缓存（Ctrl+Shift+Delete）
2. 检查文件路径是否正确（F12 -> Network）
3. 确认 static/libs/ 目录完整性：
   ```bash
   ls -la static/libs/
   ls -la static/libs/bootstrap/css/
   ls -la static/libs/bootstrap/js/
   ls -la static/libs/prismjs/
   ```

### 问题 3：图标不显示（显示方块）
**症状：** Bootstrap Icons 或 Font Awesome 显示为方块

**解决方案：**
检查字体文件是否完整：
```bash
ls -lh static/libs/bootstrap-icons/font/*.woff*
ls -lh static/libs/fontawesome/css/font-awesome.min.css
```

应该看到：
- bootstrap-icons.woff
- bootstrap-icons.woff2
- font-awesome.min.css

如果缺少，需要重新下载（参考优化方案步骤 2）

## 回滚方案

如果出现严重问题，可以快速回滚：

```bash
cd ~/git/github/lore_keeper
git checkout problem_manager/settings.py
git checkout problems/templates/problems/
rm -rf static/libs/
source venv/bin/activate
python manage.py collectstatic --noinput
```

然后重载 Web 应用。

## 技术细节

### 修改的文件列表

1. **problem_manager/settings.py**
   - 添加 STATIC_ROOT = BASE_DIR / 'staticfiles'
   - 添加 STATICFILES_DIRS = [BASE_DIR / 'static']

2. **problems/templates/problems/base.html**
   - 删除重复的 Bootstrap CSS 引用
   - 所有 CDN 链接替换为本地路径
   - 添加 defer 属性到脚本标签

3. **problems/templates/problems/problem_list.html**
   - 删除重复的 marked.js 引用
   - 删除重复的 Prism 主题 CSS
   - PrismJS 和 clipboard 替换为本地路径

4. **problems/templates/problems/problem_form.html**
   - EasyMDE 和 Font Awesome 替换为本地路径

5. **problems/templates/problems/view_detail.html**
   - 删除重复的 marked.js
   - PrismJS 和 clipboard 替换为本地路径

### 本地库文件结构

```
static/libs/
├── bootstrap/
│   ├── css/
│   │   └── bootstrap.min.css (228KB)
│   └── js/
│       └── bootstrap.bundle.min.js (79KB)
├── bootstrap-icons/
│   └── font/
│       ├── bootstrap-icons.min.css (81KB)
│       ├── bootstrap-icons.woff (161KB)
│       └── bootstrap-icons.woff2 (119KB)
├── marked/
│   └── marked.min.js (~20KB)
├── prismjs/
│   ├── prism.min.js (20KB)
│   ├── themes/
│   │   └── prism.min.css (~5KB)
│   ├── plugins/
│   │   ├── autoloader/
│   │   │   └── prism-autoloader.min.js (~10KB)
│   │   └── line-numbers/
│   │       ├── prism-line-numbers.min.js (~15KB)
│   │       └── prism-line-numbers.min.css (~5KB)
├── easymde/
│   ├── easymde.min.js (320KB)
│   └── easymde.min.css (13KB)
├── fontawesome/
│   └── css/
│       └── font-awesome.min.css (31KB)
└── clipboard/
    └── clipboard-polyfill.min.js (6.7KB)

总计：15 个文件，约 1.2MB
```

## 支持信息

如有问题，请检查：
1. PythonAnywhere 静态文件设置路径是否为 /home/用户名/git/github/lore_keeper/staticfiles
2. 静态文件 URL 是否为 /static/
3. 虚拟环境是否正确激活

---

优化完成时间：2026-02-23
优化方案：本地化所有外部 CDN 库
存储增加：1.2MB
性能提升：预计 40-50%

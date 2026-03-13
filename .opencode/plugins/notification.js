export const NotificationPlugin = async ({ project, client, $, directory, worktree }) => {
  let currentSessionName = 'unknown'

  return {
    event: async ({ event }) => {
      if (event.type === 'session.updated') {
        currentSessionName = event.properties?.info?.title || event.info?.title || currentSessionName
        return
      }

      const eventMessages = {
        //"command.executed": "Command executed",
        //"file.edited": "File edited",
        //"file.watcher.updated": "File watcher updated",
        //"installation.updated": "Installation updated",
        //"lsp.client.diagnostics": "LSP diagnostics updated",
        //"lsp.updated": "LSP updated",
        //"message.part.removed": "Message part removed",
        //"message.part.updated": "Message part updated",
        //"message.removed": "Message removed",
        //"message.updated": "Message updated",
        "permission.asked": () => {
          const perm = event.permission || event.properties?.permission
          const path = event.metadata?.filepath || event.patterns?.[0] || event.properties?.metadata?.filepath || ''
          const tool = event.tool?.messageID ? 'tool: ' + event.tool.messageID.slice(0, 8) + '...' : ''
          return 'Permission: ' + perm + '\nPath: ' + path + '\n' + tool
        },
        //"permission.replied": "permission replied",
        //"server.connected": "Server connected",
        "session.created": () => {
          currentSessionName = event.properties?.info?.title || event.info?.title || currentSessionName
          return 'Session created: ' + currentSessionName
        },
        "session.compacted": "Session compacted",
        //"session.deleted": "Session deleted",
        //"session.diff": "Session diff",
        "session.error": () => {
          const errorProps = event.properties?.error || event.data?.error || event.error
          if (errorProps?.data?.message) return errorProps.data.message
          if (errorProps?.data?.responseBody) return errorProps.data.responseBody
          if (errorProps?.message) return errorProps.message
          if (errorProps?.name) return errorProps.name + ': ' + (errorProps.message || errorProps.data?.message || '')
          return JSON.stringify(event.properties || event.data || event)
        },
        "session.idle": "Task completed, waiting for your input",
        //"session.status": () => event.properties?.status?.type || event.data?.status?.type || 'unknown',
        //"shell.env": "Shell environment updated",
        //"tool.execute.after": () => `Tool executed: ${event.data?.tool || "unknown"}`,
        //"tool.execute.before": () => `Tool executing: ${event.data?.tool || "unknown"}`,
        //"tui.prompt.append": "TUI prompt appended",
        //"tui.command.execute": () => `TUI command: ${event.data?.command || "unknown"}`,
        //"tui.toast.show": () => `Toast: ${event.data?.message || "no message"}`,
        "todo.updated": () => {
          const todos = event.todos || event.properties?.todos || event.data?.todos || []
          const symbols = { completed: '[✓]', in_progress: '[•]', pending: '[ ]' }
          return todos.map(t => (symbols[t.status] || '[ ]') + ' ' + t.content).join('\n')
        }
      }

      const getMessage = (eventType) => {
        const msg = eventMessages[eventType]
        return typeof msg === "function" ? msg() : msg
      }

      const sendNotification = async (title, message) => {
        const fullMessage = `[${currentSessionName}]\n${message}`
        try {
          await $`notify-send -u normal "opencode ${title}" "${fullMessage}"`
          await $`curl --silent --output /dev/null -d "opencode ${title} ${fullMessage}" ntfy.sh/aiagentsmessagesnotification`
        } catch (error) {
          console.log(`NotificationPlugin: notification failed: ${error.message}`)
        }
      }

      if (event.type in eventMessages) {
        const message = getMessage(event.type)
        await sendNotification(event.type, message)
      }
    }
  }
}

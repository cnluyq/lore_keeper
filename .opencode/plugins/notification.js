export const NotificationPlugin = async ({ project, client, $, directory, worktree }) => {
  return {
    event: async ({ event }) => {
      const eventMessages = {
        "command.executed": "Command executed",
        "file.edited": "File edited",
        //"file.watcher.updated": "File watcher updated",
        //"installation.updated": "Installation updated",
        "lsp.client.diagnostics": "LSP diagnostics updated",
        //"lsp.updated": "LSP updated",
        "message.part.removed": "Message part removed",
        //"message.part.updated": "Message part updated",
        "message.removed": "Message removed",
        //"message.updated": "Message updated",
        "permission.asked": () => event.data?.permission || event.data?.question || "Unknown permission",
        "permission.replied": "Permission replied",
        //"server.connected": "Server connected",
        //"session.created": "Session created",
        "session.compacted": "Session compacted",
        //"session.deleted": "Session deleted",
        //"session.diff": "Session diff",
        "session.error": () => {
          const errorProps = event.properties?.error || event.data?.error || event.error
          if (errorProps?.data?.message) return errorProps.data.message
          if (errorProps?.data?.responseBody) return errorProps.data.responseBody
          if (errorProps?.message) return errorProps.message
          if (errorProps?.name) return `${errorProps.name}: ${errorProps.message || errorProps.data?.message || ''}`
          return JSON.stringify(event.properties || event.data || event)
        },
        "session.idle": "Task complete, waiting for input",
        "session.status": () => event.properties?.status?.type || event.data?.status?.type || 'unknown',
        //"session.updated": "Session updated",
        "todo.updated": "Todo updated",
        "shell.env": "Shell environment updated",
        //"tool.execute.after": () => `Tool executed: ${event.data?.tool || "unknown"}`,
        //"tool.execute.before": () => `Tool executing: ${event.data?.tool || "unknown"}`,
        //"tui.prompt.append": "TUI prompt appended",
        "tui.command.execute": () => `TUI command: ${event.data?.command || "unknown"}`,
        "tui.toast.show": () => `Toast: ${event.data?.message || "no message"}`
      }

      const getMessage = (eventType) => {
        const msg = eventMessages[eventType]
        return typeof msg === "function" ? msg() : msg
      }

      const sendNotification = async (title, message) => {
        try {
          await $`notify-send -u normal "opencode ${title}" "${message}"`
          await $`curl --silent --output /dev/null -d "opencode ${title} ${message}" ntfy.sh/aiagentsmessagesnotification`
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

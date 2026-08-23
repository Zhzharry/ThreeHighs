import { createReadStream, existsSync, statSync } from "node:fs"
import { createServer } from "node:http"
import { extname, join, normalize, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const root = resolve(fileURLToPath(new URL(".", import.meta.url)))
const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8"
}

createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url || "/", "http://localhost").pathname)
  const requestPath = pathname === "/" ? "index.html" : pathname.replace(/^[/\\]+/, "")
  const safePath = normalize(requestPath).replace(/^(\.\.[/\\])+/, "")
  const candidate = join(root, safePath)
  const filePath = resolve(candidate)

  if (!filePath.startsWith(root) || !existsSync(filePath) || !statSync(filePath).isFile()) {
    res.writeHead(404, { "content-type": "text/plain; charset=utf-8" })
    res.end("Not found")
    return
  }

  res.writeHead(200, {
    "content-type": mimeTypes[extname(filePath)] || "application/octet-stream"
  })
  createReadStream(filePath).pipe(res)
}).listen(80, "0.0.0.0")

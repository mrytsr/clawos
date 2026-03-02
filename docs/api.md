# API Documentation

## File Operations

### Batch Copy
**Endpoint:** `POST /api/batch/copy`

**Description:** Copies multiple files or directories to a target directory.

**Request Body:**
```json
{
  "paths": ["source/file1.txt", "source/dir1"],
  "target": "destination/folder"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "copied": ["source/file1.txt", "source/dir1"],
    "errors": [],
    "message": "已复制 2 个项目"
  }
}
```

**Conflict Resolution:**
If a file with the same name exists in the target directory, the copied file is automatically renamed using the pattern `filename_counter.ext` (e.g., `file_1.txt`, `file_2.txt`).

---

### Batch Move
**Endpoint:** `POST /api/batch/move`

**Description:** Moves multiple files or directories to a target directory.

**Request Body:**
```json
{
  "paths": ["source/file1.txt", "source/dir1"],
  "target": "destination/folder"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "moved": ["source/file1.txt", "source/dir1"],
    "errors": [],
    "message": "已移动 2 个项目"
  }
}
```

**Conflict Resolution:**
If a file with the same name exists in the target directory, the moved file is automatically renamed using the pattern `filename_counter.ext`.

---

## Clipboard Logic

### LocalStorage Structure
Key: `clipboard_file_path`
Value (JSON string):
```json
{
  "type": "copy",       // or "cut"
  "paths": ["path/to/file1.txt", "path/to/dir1"], // Array of source paths
  "count": 2,           // Number of items
  "ts": 1715000000000   // Timestamp
}
```

### Floating Bar Behavior
- **Appearance:** Fixed position at bottom 10%, centered.
- **Animation:** Fade-in/out (200ms).
- **Z-Index:** 9999 (always on top).
- **Persistence:** State persists across page reloads via LocalStorage.
- **Auto-Dismiss:** Automatically removed after Paste or Cancel operation.

### Error Handling
- **Network Errors:** Displays toast "网络错误".
- **Backend Errors:** Displays toast with error message from server.
- **Invalid State:** Logs warning to console and ignores invalid LocalStorage data.

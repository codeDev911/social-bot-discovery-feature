# Backend Implementation Guide

## Step 1: Update Prisma Schema

Add this to your `prisma/schema.prisma`:

```prisma
model UserApiKey {
  id              Int       @id @default(autoincrement())
  userId          Int       @unique
  user            User      @relation(fields: [userId], references: [id], onDelete: Cascade)
  
  apiKey          String    @unique  // SHA256 hashed token
  name            String?   // e.g., "Discovery Service"
  
  isActive        Boolean   @default(true)
  lastUsedAt      DateTime?
  createdAt       DateTime  @default(now())
  expiresAt       DateTime?
  
  @@index([apiKey])
  @@index([userId])
}
```

Also update the `User` model to add the relation:

```prisma
model User {
  // ... existing fields ...
  
  apiKey          UserApiKey?
}
```

And update the `Video` model to add scraped fields:

```prisma
model Video {
  // ... existing fields ...
  
  scrapedFrom     String?      // "tiktok" | "instagram" | etc
  externalId      String?      // Platform's native ID
  keywords        String[]     // Array of keywords/topics
  
  @@index([scrapedFrom])
  @@index([externalId])
}
```

Then run:
```bash
npx prisma migrate dev --name add_api_key_and_scraped_fields
```

---

## Step 2: Add Imports to dashboard.py

Add these to the top of `routers/dashboard.py`:

```python
import secrets
import hashlib
import uuid
from datetime import datetime
```

---

## Step 3: Add API Key Request Model

Add this Pydantic model to `routers/dashboard.py` (near other request models):

```python
class GenerateApiKeyRequest(BaseModel):
    name: str = "Discovery Service"
```

---

## Step 4: Copy Endpoint Code

Copy the code from `BACKEND_ENDPOINTS.py` to your `routers/dashboard.py`.

The endpoints are:
1. `POST /api/settings/generate-api-key` - Generate new API key
2. `GET /api/settings/api-key-status` - Check API key status
3. `DELETE /api/settings/api-key` - Revoke API key
4. `POST /api/videos/ingest-discovered` - Receive discovered videos

---

## Step 5: Update Dashboard UI (Optional)

Add API key management to your dashboard settings template.

Example: `templates/dashboard/settings.html`

```html
<div class="card">
    <h3>🔑 API Key for Discovery Service</h3>
    
    <div id="apiKeyStatus">
        <!-- Loaded from API -->
    </div>
    
    <button class="btn btn-primary" onclick="generateAPIKey()">
        Generate New API Key
    </button>
    
    <div id="apiKeyDisplay" style="display:none; margin-top: 20px;">
        <div class="alert alert-warning">
            ⚠️ <strong>Save this securely!</strong> You won't see it again.
        </div>
        <div class="form-group">
            <label>Your API Key:</label>
            <div style="display: flex; gap: 10px;">
                <input type="text" id="apiKeyValue" readonly style="flex: 1;">
                <button class="btn btn-sm btn-secondary" onclick="copyToClipboard()">Copy</button>
            </div>
        </div>
    </div>
</div>

<script>
async function generateAPIKey() {
    try {
        const res = await fetch('/api/settings/generate-api-key', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        
        if (data.success) {
            document.getElementById('apiKeyValue').value = data.apiKey;
            document.getElementById('apiKeyDisplay').style.display = 'block';
            loadApiKeyStatus();
        } else {
            alert('Error: ' + (data.error || 'Failed to generate API key'));
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

function copyToClipboard() {
    const text = document.getElementById('apiKeyValue');
    text.select();
    document.execCommand('copy');
    alert('✅ API Key copied to clipboard!');
}

async function revokeApiKey() {
    if (!confirm('Are you sure? This will revoke your current API key.')) return;
    
    try {
        const res = await fetch('/api/settings/api-key', { method: 'DELETE' });
        const data = await res.json();
        
        if (data.success) {
            alert('✅ API Key revoked');
            loadApiKeyStatus();
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function loadApiKeyStatus() {
    try {
        const res = await fetch('/api/settings/api-key-status');
        const data = await res.json();
        
        let html = '';
        if (data.hasApiKey) {
            html = `
                <div class="alert alert-success">
                    ✅ <strong>API Key Active</strong>
                    <br/>Last used: ${data.lastUsedAt ? new Date(data.lastUsedAt).toLocaleString() : 'Never'}
                    <br/>Created: ${new Date(data.createdAt).toLocaleString()}
                    <button class="btn btn-sm btn-danger" style="margin-top: 10px;" onclick="revokeApiKey()">
                        Revoke Key
                    </button>
                </div>
            `;
        } else {
            html = '<p style="color: #666;">No API key generated yet. Click the button above to create one.</p>';
        }
        
        document.getElementById('apiKeyStatus').innerHTML = html;
    } catch (error) {
        console.error('Error loading API key status:', error);
    }
}

// Load status on page load
document.addEventListener('DOMContentLoaded', loadApiKeyStatus);
</script>
```

---

## Step 6: Deploy

1. Run migrations: `npx prisma migrate deploy`
2. Restart your backend
3. User can now generate API keys in dashboard
4. Add keys to GitHub Secrets
5. Discovery service will start ingesting videos

---

## Testing

### Local Test

```bash
# Generate test API key
python -c "
import secrets, hashlib
token = secrets.token_urlsafe(32)
hashed = hashlib.sha256(token.encode()).hexdigest()
print(f'Token: {token}')
print(f'Hashed: {hashed}')
"

# Use in .env
USER_API_KEY=<paste-token-here>
```

### Verify Endpoint

```bash
curl -X POST http://localhost:8000/api/videos/ingest-discovered \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "test",
    "videos": [{
      "externalId": "test123",
      "platform": "tiktok",
      "title": "Test Video",
      "description": "Test",
      "videoUrl": "https://example.com/video.mp4",
      "score": 0.8
    }]
  }'
```

---

## Files Modified

- `prisma/schema.prisma` - Added UserApiKey model and fields
- `routers/dashboard.py` - Added 4 new endpoints
- `.env` - No changes needed (secrets are in GitHub Actions)

---

## Troubleshooting

### "Relation `user` does not exist on model `UserApiKey`"
- Make sure you updated the `User` model with `apiKey UserApiKey?`
- Run migration again

### "Table does not exist"
- Run `npx prisma migrate deploy`
- Or `npx prisma db push` for development

### API key always invalid
- Check hashing: the token must be hashed with SHA256 before comparison
- Verify `Bearer ` prefix is included in Authorization header


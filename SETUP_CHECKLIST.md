# Quick Setup Checklist

Complete setup in 5 minutes:

## ✅ Phase 1: Backend Setup (Main App)

- [ ] Add `UserApiKey` model to `prisma/schema.prisma`
- [ ] Add relation to `User` and `Video` models
- [ ] Run: `npx prisma migrate dev --name add_api_key_and_scraped_fields`
- [ ] Copy code from `BACKEND_ENDPOINTS.py` to `routers/dashboard.py`
- [ ] Add imports: `secrets`, `hashlib`, `uuid`, `datetime`
- [ ] Restart backend server
- [ ] Test: Visit `/api/settings/api-key-status` (should return `{"hasApiKey": false}`)

---

## ✅ Phase 2: User API Key Generation

- [ ] User logs into dashboard
- [ ] Go to Settings → API Key for Discovery Service
- [ ] Click "Generate New API Key"
- [ ] **SAVE THE KEY** (shown only once)
- [ ] Copy User ID from dashboard

---

## ✅ Phase 3: GitHub Setup

**Go to GitHub Repository**:

Settings → Secrets and variables → Actions → New repository secret

Add these secrets:

| Name | Value |
|------|-------|
| `API_ENDPOINT` | `https://your-social-bot-url/api/videos/ingest-discovered` |
| `USER_API_KEY` | Paste the generated API key |

---

## ✅ Phase 4: Local Testing (Optional)

```bash
cd external_services/scrape_videos

# Copy .env.example to .env
cp .env.example .env

# Edit .env with your values
nano .env

# Install dependencies
pip install -r requirements.txt

# Run discovery service
python main.py

# Output should show:
# 🚀 Starting video discovery service
# 🔎 Searching [keyword]: travel pakistan
# ✅ Sent X videos - Ingested: Y
```

---

## ✅ Phase 5: GitHub Actions Trigger

**Option A: Scheduled (Automatic)**
- Service runs daily at 12 PM UTC
- Wait for next scheduled time

**Option B: Manual (Now)**
- Go to GitHub → Actions
- Select "Video Discovery Service"
- Click "Run workflow"
- Monitor logs in real-time

---

## 📋 Files to Check/Modify

### External Service (scrape_videos/)
- ✅ `config.py` - Updated to use USER_API_KEY
- ✅ `main.py` - Updated with new auth
- ✅ `ai_filter.py` - No changes
- ✅ `search.py` - No changes
- ✅ `requirements.txt` - No changes
- ✅ `.github/workflows/discover-videos.yml` - Updated secrets
- ✅ `.env.example` - Created
- ✅ `README.md` - Created

### Main App (routers/dashboard.py)
- 📝 Add imports
- 📝 Add GenerateApiKeyRequest model
- 📝 Add 4 endpoints from BACKEND_ENDPOINTS.py
- 📝 Update Prisma schema

---

## 🧪 Quick Test Commands

**Test API Key Generation:**
```bash
curl -X POST http://localhost:8000/api/settings/generate-api-key \
  -H "Cookie: session=<your-session>" \
  -H "Content-Type: application/json"
```

**Test Ingest Endpoint:**
```bash
curl -X POST http://localhost:8000/api/videos/ingest-discovered \
  -H "Authorization: Bearer <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "test",
    "videos": [{
      "externalId": "test123",
      "platform": "tiktok",
      "title": "Test",
      "description": "Test video",
      "videoUrl": "https://example.com/video.mp4",
      "score": 0.9
    }]
  }'
```

Expected response:
```json
{
  "success": true,
  "message": "1 videos ingested",
  "ingestedCount": 1,
  "userId": 1
}
```

---

## 🔧 Common Issues

| Issue | Solution |
|-------|----------|
| "USER_API_KEY not configured" | Add to GitHub Secrets or .env file |
| "Invalid or revoked API key" | Generate new key in dashboard |
| "User not found" | Key belongs to deleted user, generate new |
| "API endpoint connection error" | Check API_ENDPOINT URL in secrets |
| "No videos discovered" | Try different keywords in config.py |

---

## 📊 Monitoring

**GitHub Actions Logs:**
- Go to Actions → Video Discovery Service → Latest run
- See "Run discovery service" step output
- Watch for ✅ (success) or ❌ (errors)

**Dashboard:**
- Check "Recent Videos" to see ingested content
- Monitor video status (Pending, Processing, Uploaded)

**Database:**
- Query: `SELECT * FROM "Video" WHERE "scrapedFrom" IS NOT NULL;`
- Should see new videos with `scrapedFrom` and `externalId`

---

## 🚀 Next Steps

1. ✅ Complete backend setup
2. ✅ Generate API key
3. ✅ Add GitHub Secrets
4. ✅ Test locally (optional)
5. ✅ Manual trigger or wait for scheduled run
6. ✅ Customize search profiles in `config.py`
7. ✅ Monitor first run
8. ✅ Enjoy automated video discovery! 🎉

---

## 📞 Need Help?

1. Check `README.md` for detailed guide
2. Check `BACKEND_SETUP.md` for schema/code setup
3. Review `BACKEND_ENDPOINTS.py` for endpoint code
4. Check GitHub Actions logs for errors
5. Verify API key is active in dashboard


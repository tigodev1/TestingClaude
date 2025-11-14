# Quick Start Guide

Get your Roblox Analytics Dashboard up and running in 5 minutes!

## Step 1: Get Your Credentials

### API Key
1. Visit: https://create.roblox.com/credentials
2. Click "Create API Key"
3. Name it "Analytics Dashboard"
4. Select permissions: `universe:read` and `place:read`
5. Add IP: `0.0.0.0/0` (for testing only!)
6. **Copy the API key** - you won't see it again!

### Universe ID
1. Visit: https://create.roblox.com/dashboard/creations
2. Click your game
3. Copy the number from the URL after `/experiences/`
   - Example: `https://create.roblox.com/dashboard/creations/experiences/123456789/overview`
   - Your Universe ID is: `123456789`

## Step 2: Install Dependencies

```bash
npm run install-all
```

## Step 3: Configure

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add:
# ROBLOX_API_KEY=your_actual_api_key_here
# UNIVERSE_ID=your_universe_id_here
```

## Step 4: Run!

```bash
npm run dev
```

Open http://localhost:3000 in your browser!

## Troubleshooting

**"Configuration Required" screen?**
- Make sure you created `.env` (not `.env.example`)
- Check that both `ROBLOX_API_KEY` and `UNIVERSE_ID` are set
- Restart the server

**"Failed to fetch" error?**
- Verify your Universe ID is correct
- Check API key permissions include `universe:read`
- Make sure your IP is whitelisted in the API key settings

**Need help?**
- Check the full README.md for detailed instructions
- Look at server console for error messages

---

That's it! Your dashboard should now be displaying your Roblox game analytics!

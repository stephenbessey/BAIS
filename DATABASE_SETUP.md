# BAIS Database Setup Guide

## Understanding Railway Database URLs

Railway provides **two different database URLs**:

### 1. Internal URL (for deployed apps on Railway)
```
postgresql://postgres:password@postgres.railway.internal:5432/railway
```
- **Only works when deployed on Railway**
- Used by services running within Railway's network
- Lower latency, more secure (internal network only)
- This is what you currently have

### 2. Public URL (for local development)
```
postgresql://postgres:password@public-host.railway.app:5432/railway
```
- Works from anywhere (local machine, external servers)
- Requires a public proxy connection
- You need to get this from Railway dashboard

## Setup Options

### Option A: Use Railway Database Locally (Recommended for Testing)

1. **Get the Public DATABASE_URL from Railway:**
   - Go to your Railway project dashboard
   - Click on your PostgreSQL service
   - In the "Connect" tab, look for **PUBLIC** or **EXTERNAL** DATABASE_URL
   - It will look like: `postgresql://postgres:pass@containers-us-west-XXX.railway.app:port/railway`

2. **Set it in your local environment:**
   ```bash
   export DATABASE_URL='postgresql://postgres:pass@containers-us-west-XXX.railway.app:port/railway'
   ./start_bais.sh
   ```

3. **For permanent setup, add to your shell profile:**
   ```bash
   echo 'export DATABASE_URL="your-public-railway-url"' >> ~/.bashrc
   source ~/.bashrc
   ```

### Option B: Use Local PostgreSQL (Recommended for Development)

1. **Install PostgreSQL locally:**
   ```bash
   # macOS
   brew install postgresql@15
   brew services start postgresql@15

   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   sudo systemctl start postgresql
   ```

2. **Create local database:**
   ```bash
   createdb bais_dev
   ```

3. **Set local DATABASE_URL:**
   ```bash
   export DATABASE_URL='postgresql://localhost/bais_dev'
   # Or with user/password:
   export DATABASE_URL='postgresql://username:password@localhost:5432/bais_dev'
   ```

### Option C: Use SQLite (Simplest for Local Development)

1. **Set DATABASE_URL to use SQLite:**
   ```bash
   export DATABASE_URL='sqlite:///./bais_local.db'
   ./start_bais.sh
   ```

2. **The database file will be created automatically**
   - File: `bais_local.db` in your project directory
   - Perfect for development and testing
   - No PostgreSQL installation needed

### Option D: No Database (In-Memory Only)

1. **Don't set DATABASE_URL at all:**
   ```bash
   unset DATABASE_URL
   ./start_bais.sh
   ```

2. **The system will use in-memory storage**
   - Demo businesses are loaded automatically
   - Data is lost when server restarts
   - Perfect for quick testing

## Current Configuration

Your current DATABASE_URL:
```
postgresql://postgres:MzcvLSonfiJjECrEuIkDyKbOMYJRqjOz@postgres.railway.internal:5432/railway
```

**This is an INTERNAL Railway URL** - it will:
- ✅ Work when deployed on Railway
- ❌ NOT work when running locally

## Deployment on Railway

When deploying to Railway:

1. **Railway automatically sets DATABASE_URL** with the internal URL
2. Your app will connect to the database automatically
3. Demo business will be registered to the database on first startup
4. Data persists across restarts

## Testing Database Connection

Test your DATABASE_URL with:

```bash
export DATABASE_URL='your-database-url'
python test_db_connection.py
```

Expected output:
```
✓ DatabaseManager created successfully
✓ Tables created successfully
✓ Session working! Current business count: X
✅ Database connection test PASSED!
```

## Environment Variables

You can also use a `.env` file:

```bash
# .env
DATABASE_URL=postgresql://localhost/bais_dev
ANTHROPIC_API_KEY=your_api_key
```

The application will automatically load it on startup.

## Troubleshooting

### Error: "could not translate host name postgres.railway.internal"
**Solution**: You're using the internal Railway URL locally. Get the public URL from Railway dashboard.

### Error: "connection refused"
**Solution**: PostgreSQL is not running. Start it with `brew services start postgresql` or `sudo systemctl start postgresql`.

### Error: "database does not exist"
**Solution**: Create the database with `createdb database_name`.

### Error: "authentication failed"
**Solution**: Check your username and password in the DATABASE_URL.

## Recommended Setup for Your Use Case

Since you have a Railway PostgreSQL database, I recommend:

**For Local Development:**
```bash
# Option 1: Get public Railway URL from dashboard
export DATABASE_URL='postgresql://postgres:pass@containers-us-west-XXX.railway.app:XXXX/railway'

# Option 2: Use SQLite for local development (simplest)
export DATABASE_URL='sqlite:///./bais_local.db'

# Option 3: No database (in-memory, perfect for testing)
unset DATABASE_URL
```

**For Railway Deployment:**
- Railway automatically sets the correct DATABASE_URL
- No changes needed - it will use the internal URL
- Your app will connect to the database automatically

## Next Steps

1. Choose your setup option (A, B, C, or D above)
2. Set the appropriate DATABASE_URL
3. Run `./start_bais.sh`
4. The system will automatically:
   - Create tables if they don't exist
   - Register demo business if not already registered
   - Be ready for testing!

# WIC Loaner Device Request System

> **Note:** This app is managed by PM2, which provides process monitoring, automatic restarts, and basic failover. The system is already redundant and tolerates most failures automatically.
The troubleshooting section below is provided just in case manual intervention is needed.

## Overview

This system allows students at West Island College (WIC) to request loaner laptops or chargers. It automates ticket creation in Freshdesk, sends confirmation emails, and provides a modern, branded user experience. The system is built with **Next.js**, **React**, **Tailwind CSS**, and runs on a Linux VM with PM2.

## 🆕 New Features - Dynamic User Management

### Microsoft 365 Integration
The system now automatically fetches the latest user data from Microsoft 365:

- **Real-time Staff Data** - Automatically syncs staff information including departments, job titles, and office locations
- **Dynamic Student Lists** - Fetches 698+ student users from designated Microsoft 365 groups
- **Live User Updates** - No more manual user list maintenance - data is always current
- **Automatic Synchronization** - Runs every 6 hours to ensure user data is up-to-date

### API Endpoints
- **`/api/staff-emails`** - Staff email lookups for form dropdowns
- **`/api/staff-users`** - Comprehensive staff information from Microsoft 365
- **`/api/students`** - Student user data (698+ users from Microsoft 365 groups)
- **`/api/teachers`** - Teacher user management
- **`/api/devices`** - Available loaner devices from Snipe-IT

### Benefits
- ✅ **Always Current** - User lists automatically update from Microsoft 365
- ✅ **No Manual Work** - System handles user synchronization automatically
- ✅ **Comprehensive Data** - Includes full staff profiles with departments and titles
- ✅ **Real-time Access** - Form dropdowns show current user information

### Microsoft 365 Integration
The system now automatically fetches the latest user data from Microsoft 365:

- **Real-time Staff Data** - Automatically syncs staff information including departments, job titles, and office locations
- **Dynamic Student Lists** - Fetches 698+ student users from designated Microsoft 365 groups
- **Live User Updates** - No more manual user list maintenance - data is always current
- **Automatic Synchronization** - Runs every 6 hours to ensure user data is up-to-date

### API Endpoints
- **`/api/staff-emails`** - Staff email lookups for form dropdowns
- **`/api/staff-users`** - Comprehensive staff information from Microsoft 365
- **`/api/students`** - Student user data (698+ users from Microsoft 365 groups)
- **`/api/teachers`** - Teacher user management
- **`/api/devices`** - Available loaner devices from Snipe-IT

### Benefits
- ✅ **Always Current** - User lists automatically update from Microsoft 365
- ✅ **No Manual Work** - System handles user synchronization automatically
- ✅ **Comprehensive Data** - Includes full staff profiles with departments and titles
- ✅ **Real-time Access** - Form dropdowns show current user information

---

## What To Do If The System Fails or Goes Down

### 1. **Check if the App is Running**
```bash
pm2 list
```
- If the status is not "online", restart:
```bash
pm2 restart loanerform
```

### 2. **Check Logs for Errors**
```bash
pm2 logs loanerform
```
- Look for errors related to port conflicts, build failures, or missing dependencies.

### 3. **Rebuild the App**
If you suspect a build or dependency issue:
```bash
cd /path/to/loanerform
npm install
npm run build
pm2 restart loanerform
```

### 4. **Check Port Conflicts**
If the app won't start, check if port 3000 is already in use:
```bash
lsof -i :3000
```
- Kill any conflicting processes:
```bash
kill -9 <PID>
```

### 5. **Verify Environment Variables**
Ensure all required environment variables are set in `.env.local`:
```env
AZURE_CLIENT_ID=your_microsoft_365_client_id
AZURE_CLIENT_SECRET=your_microsoft_365_client_secret
AZURE_TENANT_ID=your_microsoft_365_tenant_id
SNIPE_IT_URL=your_snipeit_instance_url
SNIPE_IT_API_TOKEN=your_snipeit_api_token
```

### 6. **Check Microsoft 365 API Access**
If user data isn't loading:
- Verify Microsoft Graph API permissions
- Check if the app registration is still active
- Ensure group membership access is correct

### 7. **Restart the Entire System (Last Resort)**
If all else fails:
```bash
sudo reboot
# After reboot, check if PM2 auto-starts the app
pm2 list
```

## System Architecture

- **Frontend**: Next.js 14 with React and TypeScript
- **Styling**: Tailwind CSS for responsive design
- **Backend**: API routes for user management and device inventory
- **External APIs**: Microsoft 365 Graph API, Snipe-IT API
- **Process Management**: PM2 for monitoring and auto-restart
- **Deployment**: Linux VM with automatic failover

## User Data Sources

### Microsoft 365 Groups
- **Staff Users**: Comprehensive staff profiles with departments and job titles
- **Students**: 698+ student users from designated groups
- **Teachers**: Teacher-specific user management

### Snipe-IT Integration
- **Device Inventory**: Real-time loaner device availability
- **Category Focus**: Student loaner laptops (category ID 12)
- **Status Tracking**: Device checkout and availability monitoring

## Monitoring and Maintenance

### Daily Checks
- Verify PM2 status: `pm2 list`
- Check recent logs: `pm2 logs loanerform --lines 50`
- Monitor user data sync status in application logs

### Weekly Maintenance
- Review error logs for patterns
- Verify Microsoft 365 API access
- Check Snipe-IT connectivity

### Monthly Tasks
- Update dependencies: `npm update`
- Review and rotate API credentials if needed
- Monitor system performance and resource usage

---

**Built for West Island College with ❤️ and modern web technologies**

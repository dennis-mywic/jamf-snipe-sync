#!/bin/bash
#
# Renew SSL Certificate for snipe.mywic.ca
# Run this on the VM (172.22.2.169) as itsystems user with sudo
#

set -e

DOMAIN="snipe.mywic.ca"
EMAIL="dennis@mywic.ca"  # Update if needed

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║           SSL Certificate Renewal for snipe.mywic.ca                      ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
    echo "✅ Certbot installed"
else
    echo "✅ Certbot already installed"
fi

# Check current certificate status
echo ""
echo "📋 Current certificate status:"
echo "─────────────────────────────────────────────────────────────────────────────"
sudo certbot certificates 2>&1 | grep -A 15 "$DOMAIN" || echo "No existing certificate found for $DOMAIN"

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  Renewing SSL Certificate"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Renew or obtain certificate
if sudo certbot certificates 2>&1 | grep -q "$DOMAIN"; then
    echo "🔄 Renewing existing certificate for $DOMAIN..."
    sudo certbot renew --cert-name $DOMAIN --nginx
else
    echo "🆕 Obtaining new certificate for $DOMAIN..."
    sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email $EMAIL
fi

# Check if renewal was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SSL certificate renewed successfully!"
    echo ""
    
    # Reload nginx
    echo "🔄 Reloading nginx..."
    sudo systemctl reload nginx || sudo systemctl restart nginx
    echo "✅ Nginx reloaded"
    
    # Show new certificate info
    echo ""
    echo "📋 Updated certificate info:"
    echo "─────────────────────────────────────────────────────────────────────────────"
    sudo certbot certificates 2>&1 | grep -A 15 "$DOMAIN"
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════════════╗"
    echo "║                        ✅ SSL RENEWAL COMPLETE                             ║"
    echo "╚════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Certificate for $DOMAIN has been renewed"
    echo "Nginx has been reloaded with new certificate"
    echo ""
    echo "🔍 Verify at: https://$DOMAIN"
    echo ""
else
    echo ""
    echo "❌ SSL renewal failed"
    echo ""
    echo "Common issues:"
    echo "  1. Port 80/443 not accessible from internet"
    echo "  2. DNS not pointing to this server"
    echo "  3. Nginx not configured properly"
    echo ""
    echo "Try manual renewal:"
    echo "  sudo certbot renew --dry-run"
    echo ""
fi

# Set up auto-renewal (if not already set)
echo "═══════════════════════════════════════════════════════════════════════════"
echo "  Setting up auto-renewal"
echo "═══════════════════════════════════════════════════════════════════════════"

# Check if certbot timer exists
if sudo systemctl list-timers | grep -q certbot; then
    echo "✅ Certbot auto-renewal timer already enabled"
    sudo systemctl status certbot.timer --no-pager | head -5
else
    echo "⚙️  Enabling certbot auto-renewal..."
    sudo systemctl enable certbot.timer
    sudo systemctl start certbot.timer
    echo "✅ Auto-renewal enabled"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "✅ SSL renewal complete and auto-renewal configured"
echo "   Certificates will auto-renew before expiration"
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""


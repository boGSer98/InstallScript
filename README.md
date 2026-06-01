# [Odoo](https://www.odoo.com "Odoo's Homepage") Install Script X86 X32 ARM
# Arch detection + wkhtmltopdf via Ubuntu repos (arm64/amd64/i386)

This script is based on the install script from André Schenkels (https://github.com/aschenkels-ictstudio/openerp-install-scripts)
but goes a bit further and has been improved. This script will also give you the ability to define an xmlrpc_port in the .conf file that is generated under /etc/
This script can be safely used in a multi-odoo code base server because the default Odoo port is changed BEFORE the Odoo is started.

## Installing Nginx
If you set the parameter ```INSTALL_NGINX``` to ```True``` you should also configure workers. Without workers you will probably get connection loss issues. Look at [the deployment guide from Odoo](https://www.odoo.com/documentation/19.0/administration/install/deploy.html) on how to configure workers.

The generated Nginx configuration enables Odoo proxy mode and includes separate upstreams for the main HTTP service and the longpolling/websocket service. The `/websocket` route is configured with HTTP/1.1 upgrade headers so Odoo realtime features can work behind the reverse proxy.

## Installation procedure

##### 1. Download the script:
```
sudo wget https://raw.githubusercontent.com/Yenthe666/InstallScript/19.0/odoo_install.sh
```
##### 2. Modify the parameters as you wish.
There are a few things you can configure, this is the most used list:<br/>
```OE_USER``` will be the username for the system user.<br/>
```GENERATE_RANDOM_PASSWORD``` if this is set to ```True``` the script will generate a random password, if set to ```False```we'll set the password that is configured in ```OE_SUPERADMIN```. By default the value is ```True``` and the script will generate a random and secure password.<br/>
```INSTALL_WKHTMLTOPDF``` set to ```False``` if you do not want to install Wkhtmltopdf, if you want to install it you should set it to ```True```.<br/>
```OE_PORT``` is the port where Odoo should run on, for example 8069.<br/>
```OE_VERSION``` is the Odoo version to install, for example ```19.0``` for Odoo V19.<br/>
```IS_ENTERPRISE``` will install the Enterprise version on top of ```19.0``` if you set it to ```True```, set it to ```False``` if you want the community version of Odoo 19.<br/>
```UPGRADE_TO_ENTERPRISE``` set to ```True``` on an existing Community installation to clone/update Enterprise addons, update the generated ```addons_path```, restart Odoo, and exit without rerunning the full installer.<br/>
```CUSTOM_ADDONS_PATH``` is the custom addons directory. It defaults to ```/odoo/custom/addons``` and is always kept in ```addons_path```, including Enterprise installations and later Enterprise upgrades.<br/>
```OE_SUPERADMIN``` is the master password for this Odoo installation.<br/>
```INSTALL_NGINX``` is set to ```False``` by default. Set this to ```True``` if you want to install Nginx.<br/>
```GRANT_ODOO_SUDO``` is set to ```False``` by default. The Odoo service user normally does not need sudo privileges; only set this to ```True``` for special custom workflows that explicitly require it.<br/>
```WEBSITE_NAME``` Set the website name here for nginx configuration<br/>
```ENABLE_SSL``` Set this to ```True``` to install [certbot](https://github.com/certbot/certbot) and configure nginx with https using a free Let's Encrypted certificate<br/>
```ADMIN_EMAIL``` Email is needed to register for Let's Encrypt registration. Replace the default placeholder with an email of your organisation.<br/>
```INSTALL_NGINX``` and ```ENABLE_SSL``` must be set to ```True``` and the placeholder in ```ADMIN_EMAIL``` must be replaced with a valid email address for certbot installation<br/>
  _By enabling SSL though Let's Encrypt you agree to the following [policies](https://www.eff.org/code/privacy/policy)_ <br/>

#### 3. Make the script executable
```
sudo chmod +x odoo_install.sh
```

#### Validate local script changes
If you modify the installer, run the lightweight validation before committing:
```
scripts/validate.sh
```
The validator checks Bash syntax and runs ShellCheck when it is installed.

##### 4. Execute the script:
```
sudo ./odoo_install.sh
```

## Security notes

The generated Odoo configuration file at `/etc/${OE_CONFIG}.conf` contains the master password (`admin_passwd`). The installer creates it with owner `${OE_USER}:${OE_USER}` and mode `640` before writing any content, so it is not world-readable while secrets are being written.

The final success summary does not print the master password value. To retrieve it deliberately on the server, read it from the protected config file:
```
sudo grep '^admin_passwd = ' /etc/${OE_CONFIG}.conf
```

The installer validates operator-editable scalar values before running package installation or file writes. Boolean flags must be `True` or `False`, ports must be numeric and within `1-65535`, identifiers such as `OE_USER` and `OE_CONFIG` may only contain letters, numbers, underscores, and dashes, and custom/enterprise addon paths must be absolute managed paths outside critical system roots such as `/`, `/etc`, `/usr`, `/var`, `/home`, `/root`, and `/opt`.

Long-running package, network, and Git commands are wrapped with `run_with_timeout` and default to `COMMAND_TIMEOUT_SECONDS="1800"` (30 minutes). Adjust this variable before running the installer if a slow customer connection legitimately needs more time.

PostgreSQL readiness probes are also bounded. After the installer starts PostgreSQL for Enterprise pgvector setup, `wait_for_postgresql` gives `pg_isready` up to `POSTGRES_READY_TIMEOUT_SECONDS="120"` seconds before failing with a clear error instead of waiting forever.

Runtime artifacts are written idempotently where possible. The log directory is created with `install -d` so reruns can reuse it safely, and `start.sh` is overwritten in one pass instead of appended to on every run.

Nginx site activation is rerun-safe: the generated site symlink is updated with `ln -sf`, and removal of the default site uses `rm -f` so the step does not fail if the default site was already removed.

Fallback wkhtmltopdf binary links are also rerun-safe. If `/usr/local/bin/wkhtmltopdf` or `/usr/local/bin/wkhtmltoimage` exists but is not on `PATH`, the installer updates explicit `/usr/bin/...` symlinks with `ln -sf` instead of failing on reruns.

Odoo source checkout is resumable. If `${OE_HOME_EXT}` is already a Git checkout, the installer fetches, checks out, and fast-forwards the configured `${OE_VERSION}` as `${OE_USER}` instead of running a second `git clone`. If the target path exists but is not a Git checkout, the installer stops with a clear error instead of overwriting unknown data.

Enterprise addons checkout follows the same resumable pattern. If `${ENTERPRISE_ADDONS_PATH}` is already a Git checkout, the installer updates it in place as `${OE_USER}`; if the path exists but is not a Git checkout, the installer aborts instead of deleting or replacing existing data.

When Nginx is enabled, the installer sets `proxy_mode = True` idempotently. Existing `proxy_mode` entries are removed before the value is appended, so repeated runs do not duplicate the option in `/etc/${OE_CONFIG}.conf`.

## Custom addons

By default the installer creates and uses:
```
/odoo/custom/addons
```

You can change this with `CUSTOM_ADDONS_PATH` before running the installer. The path is written to `addons_path` for both Community and Enterprise installations, so your custom modules remain available if you later switch the same installation to Enterprise.

## Upgrade an existing Community installation to Enterprise addons

On an already installed Community server, set:
```
UPGRADE_TO_ENTERPRISE="True"
```

Then run the script again:
```
sudo ./odoo_install.sh
```

In this mode the script only installs/synchronizes Enterprise addons, updates `/etc/${OE_CONFIG}.conf` so `addons_path` contains Enterprise, Odoo standard addons, and `CUSTOM_ADDONS_PATH`, restarts Odoo, and exits without rerunning the full installer.

## Where should I host Odoo?
There are plenty of great services that offer good hosting. The script has been tested with a few major players such as [Google Cloud](https://cloud.google.com/), [Hetzner](https://www.hetzner.com/), [Amazon AWS](https://aws.amazon.com/) and [DigitalOcean](https://www.digitalocean.com/products/droplets/).
If you'd like you can use my [DigitalOcean referral link](https://m.do.co/c/d605cc420682) which gives you a 200$ voucher for free for the first 60 days.

## Minimal server requirements
While technically you can run an Odoo instance on 1GB (1024MB) of RAM it is absolutely not advised. A Linux instance typically uses 300MB-500MB and the rest has to be split among Odoo, postgreSQL and others. If you install an Odoo you should make sure to use at least 2GB of RAM. This script might fail with less resources too.
There are known issues on DigitalOcean for example where the installation crashes on 1GB RAM machines. See https://github.com/Yenthe666/InstallScript/issues/243


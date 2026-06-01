import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
UBUNTU_SCRIPT = (REPO_ROOT / "odoo_install.sh").read_text()


class InstallerFeatureTests(unittest.TestCase):
    def test_custom_addons_path_is_configurable_and_used_in_addons_path(self):
        self.assertIn('CUSTOM_ADDONS_PATH="${OE_HOME}/custom/addons"', UBUNTU_SCRIPT)
        self.assertIn('sudo install -d -o "$OE_USER" -g "$OE_USER" "$CUSTOM_ADDONS_PATH"', UBUNTU_SCRIPT)
        self.assertIn("${CUSTOM_ADDONS_PATH}", UBUNTU_SCRIPT)

    def test_enterprise_addons_path_keeps_custom_addons_available(self):
        self.assertIn('ENTERPRISE_ADDONS_PATH="${OE_HOME}/enterprise/addons"', UBUNTU_SCRIPT)
        expected = "addons_path=${ENTERPRISE_ADDONS_PATH},${OE_HOME_EXT}/addons,${CUSTOM_ADDONS_PATH}"
        self.assertIn(expected, UBUNTU_SCRIPT)

    def test_installer_supports_idempotent_enterprise_upgrade_mode(self):
        self.assertIn('UPGRADE_TO_ENTERPRISE="False"', UBUNTU_SCRIPT)
        self.assertIn("upgrade_to_enterprise()", UBUNTU_SCRIPT)
        self.assertIn("sed -i", UBUNTU_SCRIPT)
        expected = "sudo su root -c \"printf 'addons_path=${ENTERPRISE_ADDONS_PATH},${OE_HOME_EXT}/addons,${CUSTOM_ADDONS_PATH}\\n'"
        self.assertIn(expected, UBUNTU_SCRIPT)

    def test_odoo_user_does_not_get_sudo_by_default(self):
        self.assertIn('GRANT_ODOO_SUDO="False"', UBUNTU_SCRIPT)
        self.assertIn('if [ "$GRANT_ODOO_SUDO" = "True" ]; then', UBUNTU_SCRIPT)
        self.assertNotIn("sudo adduser $OE_USER sudo\n", UBUNTU_SCRIPT)

    def test_odoo_config_file_is_created_with_restrictive_permissions(self):
        self.assertIn(
            'sudo install -m 640 -o "$OE_USER" -g "$OE_USER" /dev/null "/etc/${OE_CONFIG}.conf"',
            UBUNTU_SCRIPT,
        )
        self.assertNotIn("sudo touch /etc/${OE_CONFIG}.conf", UBUNTU_SCRIPT)
        self.assertIn("cat <<EOF | sudo tee \"/etc/${OE_CONFIG}.conf\" >/dev/null", UBUNTU_SCRIPT)
        self.assertIn("admin_passwd = ${OE_SUPERADMIN}", UBUNTU_SCRIPT)

    def test_final_summary_does_not_print_master_password_value(self):
        self.assertNotIn('echo "Password superadmin (database): $OE_SUPERADMIN"', UBUNTU_SCRIPT)
        self.assertIn('echo "Password superadmin (database): <stored in /etc/${OE_CONFIG}.conf>"', UBUNTU_SCRIPT)
        self.assertIn("sudo grep '^admin_passwd = ' /etc/${OE_CONFIG}.conf", UBUNTU_SCRIPT)

    def test_installer_validates_paths_and_scalar_inputs_before_running(self):
        self.assertIn("validate_config()", UBUNTU_SCRIPT)
        self.assertIn('validate_managed_path "CUSTOM_ADDONS_PATH" "$CUSTOM_ADDONS_PATH"', UBUNTU_SCRIPT)
        self.assertIn('validate_managed_path "ENTERPRISE_ADDONS_PATH" "$ENTERPRISE_ADDONS_PATH"', UBUNTU_SCRIPT)
        self.assertIn('validate_identifier "OE_USER" "$OE_USER"', UBUNTU_SCRIPT)
        self.assertIn('require_no_newline "OE_SUPERADMIN" "$OE_SUPERADMIN"', UBUNTU_SCRIPT)
        self.assertIn('fail_config "$name" "refusing dangerous path"', UBUNTU_SCRIPT)
        self.assertIn('detect_arch\nvalidate_config', UBUNTU_SCRIPT)

    def test_nginx_config_supports_odoo_websocket_and_proxy_mode(self):
        self.assertIn("map \\$http_upgrade \\$connection_upgrade", UBUNTU_SCRIPT)
        self.assertIn("upstream odoo {", UBUNTU_SCRIPT)
        self.assertIn("upstream odoochat {", UBUNTU_SCRIPT)
        self.assertIn("proxy_set_header Host \\$host;", UBUNTU_SCRIPT)
        self.assertIn("location /websocket {", UBUNTU_SCRIPT)
        self.assertIn("proxy_http_version 1.1;", UBUNTU_SCRIPT)
        self.assertIn("proxy_set_header Upgrade \\$http_upgrade;", UBUNTU_SCRIPT)
        self.assertIn("proxy_set_header Connection \\$connection_upgrade;", UBUNTU_SCRIPT)
        self.assertIn("proxy_pass http://odoochat;", UBUNTU_SCRIPT)
        self.assertIn('set_config_value "proxy_mode" "True" "/etc/${OE_CONFIG}.conf"', UBUNTU_SCRIPT)

    def test_long_running_network_commands_have_timeouts(self):
        self.assertIn('COMMAND_TIMEOUT_SECONDS="1800"', UBUNTU_SCRIPT)
        self.assertIn("run_with_timeout()", UBUNTU_SCRIPT)
        self.assertIn('timeout "$COMMAND_TIMEOUT_SECONDS" "$@"', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo apt-get update -y', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo apt-get upgrade -y', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo -u "$OE_USER" git clone --depth 1 --branch "$OE_VERSION"', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo npm install -g rtlcss', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo snap install --classic certbot', UBUNTU_SCRIPT)

    def test_postgresql_readiness_wait_is_bounded(self):
        self.assertIn('POSTGRES_READY_TIMEOUT_SECONDS="120"', UBUNTU_SCRIPT)
        self.assertIn("wait_for_postgresql()", UBUNTU_SCRIPT)
        self.assertIn('while ! sudo -u postgres pg_isready >/dev/null 2>&1; do', UBUNTU_SCRIPT)
        self.assertIn('if [ "$elapsed" -ge "$POSTGRES_READY_TIMEOUT_SECONDS" ]; then', UBUNTU_SCRIPT)
        self.assertIn('PostgreSQL did not become ready within ${POSTGRES_READY_TIMEOUT_SECONDS}s', UBUNTU_SCRIPT)
        self.assertNotIn('until sudo -u postgres pg_isready >/dev/null 2>&1; do sleep 1; done', UBUNTU_SCRIPT)

    def test_runtime_files_are_written_idempotently(self):
        self.assertIn('sudo install -d -o "$OE_USER" -g "$OE_USER" "/var/log/$OE_USER"', UBUNTU_SCRIPT)
        self.assertNotIn('sudo mkdir /var/log/$OE_USER', UBUNTU_SCRIPT)
        self.assertIn('cat <<EOF | sudo tee "$OE_HOME_EXT/start.sh" >/dev/null', UBUNTU_SCRIPT)
        self.assertIn('sudo chown "$OE_USER:$OE_USER" "$OE_HOME_EXT/start.sh"', UBUNTU_SCRIPT)
        self.assertNotIn('>> $OE_HOME_EXT/start.sh', UBUNTU_SCRIPT)

    def test_nginx_site_activation_is_idempotent(self):
        self.assertIn('sudo ln -sf "/etc/nginx/sites-available/$WEBSITE_NAME" "/etc/nginx/sites-enabled/$WEBSITE_NAME"', UBUNTU_SCRIPT)
        self.assertIn('sudo rm -f /etc/nginx/sites-enabled/default', UBUNTU_SCRIPT)
        self.assertNotIn('sudo ln -s /etc/nginx/sites-available/$WEBSITE_NAME /etc/nginx/sites-enabled/$WEBSITE_NAME', UBUNTU_SCRIPT)
        self.assertNotIn('sudo rm /etc/nginx/sites-enabled/default', UBUNTU_SCRIPT)

    def test_wkhtmltopdf_binary_symlinks_are_idempotent(self):
        self.assertIn('sudo ln -sf /usr/local/bin/wkhtmltopdf /usr/bin/wkhtmltopdf', UBUNTU_SCRIPT)
        self.assertIn('sudo ln -sf /usr/local/bin/wkhtmltoimage /usr/bin/wkhtmltoimage', UBUNTU_SCRIPT)
        self.assertNotIn('sudo ln -s /usr/local/bin/wkhtmltopdf /usr/bin || true', UBUNTU_SCRIPT)
        self.assertNotIn('sudo ln -s /usr/local/bin/wkhtmltoimage /usr/bin || true', UBUNTU_SCRIPT)

    def test_odoo_source_checkout_is_idempotent(self):
        self.assertIn('sync_odoo_source() {', UBUNTU_SCRIPT)
        self.assertIn('if [ -d "$OE_HOME_EXT/.git" ]; then', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo -u "$OE_USER" git -C "$OE_HOME_EXT" fetch origin "$OE_VERSION"', UBUNTU_SCRIPT)
        self.assertIn('sudo -u "$OE_USER" git -C "$OE_HOME_EXT" checkout "$OE_VERSION"', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo -u "$OE_USER" git -C "$OE_HOME_EXT" pull --ff-only origin "$OE_VERSION"', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo -u "$OE_USER" git clone --depth 1 --branch "$OE_VERSION" https://www.github.com/odoo/odoo "$OE_HOME_EXT/"', UBUNTU_SCRIPT)
        self.assertNotIn('run_with_timeout sudo git clone --depth 1 --branch "$OE_VERSION" https://www.github.com/odoo/odoo "$OE_HOME_EXT/"', UBUNTU_SCRIPT)

    def test_enterprise_addons_checkout_is_idempotent(self):
        self.assertIn('sync_enterprise_addons() {', UBUNTU_SCRIPT)
        self.assertIn('if [ -d "$ENTERPRISE_ADDONS_PATH/.git" ]; then', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo -u "$OE_USER" git -C "$ENTERPRISE_ADDONS_PATH" fetch origin "$OE_VERSION"', UBUNTU_SCRIPT)
        self.assertIn('sudo -u "$OE_USER" git -C "$ENTERPRISE_ADDONS_PATH" checkout "$OE_VERSION"', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo -u "$OE_USER" git -C "$ENTERPRISE_ADDONS_PATH" pull --ff-only origin "$OE_VERSION"', UBUNTU_SCRIPT)
        self.assertIn('Cannot clone Enterprise addons: $ENTERPRISE_ADDONS_PATH already exists but is not a Git checkout.', UBUNTU_SCRIPT)
        self.assertIn('run_with_timeout sudo -u "$OE_USER" git clone --depth 1 --branch "$OE_VERSION" https://www.github.com/odoo/enterprise "$ENTERPRISE_ADDONS_PATH"', UBUNTU_SCRIPT)
        self.assertNotIn('sudo rm -rf "$ENTERPRISE_ADDONS_PATH"', UBUNTU_SCRIPT)

    def test_proxy_mode_is_written_idempotently(self):
        self.assertIn('set_config_value() {', UBUNTU_SCRIPT)
        self.assertIn('set_config_value "proxy_mode" "True" "/etc/${OE_CONFIG}.conf"', UBUNTU_SCRIPT)
        self.assertIn('sudo sed -i "/^${key} = /d;/^${key}=/d" "$config_file"', UBUNTU_SCRIPT)
        self.assertIn('printf \'%s = %s\\n\' "$key" "$value" | sudo tee -a "$config_file" >/dev/null', UBUNTU_SCRIPT)
        self.assertNotIn('sudo su root -c "printf \'proxy_mode = True\\n\' >> /etc/${OE_CONFIG}.conf"', UBUNTU_SCRIPT)


if __name__ == "__main__":
    unittest.main()

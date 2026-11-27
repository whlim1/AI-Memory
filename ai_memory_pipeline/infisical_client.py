#!/usr/bin/env python3
"""
Infisical Client for AI Memory Platform.

This module provides utilities to interact with Infisical secrets management.
It fetches secrets from Infisical and generates docker-compose configuration files.

Usage:
    python infisical_client.py --fetch-secrets --output docker-compose.monitoring.yml
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error


class InfisicalClient:
    """Client for interacting with Infisical secrets management."""
    
    def __init__(self, url: str, project_id: str, client_id: str = None, secret_key: str = None):
        """
        Initialize the Infisical client.
        
        Args:
            url: URL of the Infisical server (e.g., http://localhost:8081)
            project_id: Infisical project ID
            client_id: Infisical client ID (for authentication)
            secret_key: Infisical client secret key (for authentication)
        """
        self.url = url.rstrip('/')
        self.project_id = project_id
        self.client_id = client_id
        self.secret_key = secret_key
        self._access_token = None
        
    def _authenticate(self) -> str:
        """
        Exchange client_id + secret_key for a bearer token via service account flow.
        
        Returns:
            Access token string
            
        Raises:
            Exception: If authentication fails
        """
        if not self.client_id or not self.secret_key:
            raise Exception("Client ID and secret key are required for authentication")
        
        auth_url = f"{self.url}/api/v1/service-account-keys/generate-access-token"
        auth_data = json.dumps({
            "clientID": self.client_id,
            "clientSecret": self.secret_key
        }).encode('utf-8')
        
        headers = {'Content-Type': 'application/json'}
        request = urllib.request.Request(auth_url, method='POST', headers=headers, data=auth_data)
        
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode())
                self._access_token = result['accessToken']
                return self._access_token
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else ''
            raise Exception(f"Authentication failed: {e.code} {e.reason} - {error_body}")
        except Exception as e:
            raise Exception(f"Authentication request failed: {e}")
    
    def _get_auth_headers(self) -> dict:
        """Get headers with valid authentication token."""
        headers = {'Content-Type': 'application/json'}
        if self.client_id and self.secret_key:
            if not self._access_token:
                self._authenticate()
            headers['Authorization'] = f'Bearer {self._access_token}'
        return headers
    
    def _make_request(self, endpoint: str, method: str = 'GET', data: dict = None) -> dict:
        """
        Make a request to the Infisical API.
        
        Args:
            endpoint: API endpoint (e.g., /api/v1/projects/{projectId}/secrets)
            method: HTTP method
            data: Request body for POST/PUT requests
            
        Returns:
            JSON response as dictionary
        """
        url = f"{self.url}{endpoint}"
        headers = self._get_auth_headers()
        
        body = json.dumps(data).encode('utf-8') if data else None
        
        request = urllib.request.Request(url, method=method, headers=headers, data=body)
        
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if hasattr(e, 'read') else ''
            print(f"HTTP Error {e.code}: {e.reason}")
            print(f"Response: {error_body}")
            # If token is expired/invalid, try re-authenticating once
            if e.code in (401, 403) and self.client_id and self.secret_key:
                self._access_token = None
                self._authenticate()
                headers = self._get_auth_headers()
                request = urllib.request.Request(url, method=method, headers=headers, data=body)
                with urllib.request.urlopen(request, timeout=10) as response:
                    return json.loads(response.read().decode())
            raise
        except Exception as e:
            print(f"Request failed: {e}")
            raise
    
    def get_secrets(self, environment: str = "production") -> dict:
        """
        Fetch secrets from Infisical.
        
        Args:
            environment: Environment name (default: "production")
            
        Returns:
            Dictionary of secret names and values
        """
        # Service account API endpoint
        endpoint = f"/api/v1/projects/{self.project_id}/secrets?environment={environment}"
        
        try:
            response = self._make_request(endpoint)
            
            # Handle Infisical response format
            secrets = {}
            if 'secrets' in response:
                for secret in response['secrets']:
                    key = secret.get('secretKey', '')
                    value = secret.get('secretValue', '')
                    if key and value:
                        secrets[key] = value
            return secrets
            
        except Exception as e:
            print(f"Failed to fetch secrets from {endpoint}: {e}")
            return {}
    
    def get_secret(self, key: str) -> str:
        """
        Get a specific secret value by key.
        
        Args:
            key: Secret name
            
        Returns:
            Secret value or None if not found
        """
        secrets = self.get_secrets()
        return secrets.get(key)


def generate_monitoring_compose(secrets: dict, output_path: str) -> None:
    """
    Generate docker-compose.monitoring.yml from Infisical secrets.
    
    Args:
        secrets: Dictionary of secret names and values
        output_path: Path to write the generated file
    """
    # Get secrets with defaults
    grafana_admin_password = secrets.get('grafana_admin_password', 'admin')
    qdrant_api_key = secrets.get('qdrant_api_key', '')
    
    compose_config = {
        'version': '3.8',
        'services': {
            'prometheus': {
                'image': 'prom/prometheus:latest',
                'container_name': 'monitoring_prometheus',
                'ports': ['9090:9090'],
                'volumes': ['./prometheus.yml:/etc/prometheus/prometheus.yml', './prometheus_data:/prometheus'],
                'restart': 'unless-stopped',
                'networks': ['monitoring']
            },
            'grafana': {
                'image': 'grafana/grafana:latest',
                'container_name': 'monitoring_grafana',
                'ports': ['3000:3000'],
                'environment': [
                    f'GF_SECURITY_ADMIN_PASSWORD={grafana_admin_password}'
                ],
                'volumes': ['./grafana_data:/var/lib/grafana'],
                'restart': 'unless-stopped',
                'networks': ['monitoring']
            },
            'node-exporter': {
                'image': 'prom/node-exporter:latest',
                'container_name': 'monitoring_node_exporter',
                'ports': ['9100:9100'],
                'volumes': ['/proc:/host/proc:ro', '/sys:/host/sys:ro'],
                'restart': 'unless-stopped',
                'networks': ['monitoring']
            },
            'qdrant-exporter': {
                'image': 'quay.io/prometheuscommunity/qdrant-exporter:latest',
                'container_name': 'monitoring_qdrant_exporter',
                'ports': ['8888:8888'],
                'environment': [
                    f'QDRANT_URL=http://192.168.0.16:6333',
                    f'QDRANT_API_KEY={qdrant_api_key}'
                ],
                'restart': 'unless-stopped',
                'networks': ['monitoring']
            }
        },
        'networks': {
            'monitoring': {
                'driver': 'bridge'
            }
        }
    }
    
    # Write to file
    with open(output_path, 'w') as f:
        json.dump(compose_config, f, indent=2)
    
    print(f"Generated {output_path}")
    print(f"  Grafana admin password: {grafana_admin_password}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Infisical Client for AI Memory Platform')
    parser.add_argument('--url', default=os.environ.get('INFISICAL_URL', 'http://192.168.0.16:8081'),
                        help='Infisical server URL')
    parser.add_argument('--project-id', default=os.environ.get('INFISICAL_PROJECT_ID', ''),
                        help='Infisical project ID')
    parser.add_argument('--client-id', default=os.environ.get('INFISICAL_CLIENT_ID', ''),
                        help='Infisical client ID')
    parser.add_argument('--secret-key', default=os.environ.get('INFISICAL_SECRET_KEY', ''),
                        help='Infisical client secret key')
    parser.add_argument('--output', '-o', default='docker-compose.monitoring.yml',
                        help='Output file for generated docker-compose config')
    
    args = parser.parse_args()
    
    # Validate required parameters
    if not args.project_id:
        print("Error: Project ID is required. Set INFISICAL_PROJECT_ID or use --project-id")
        sys.exit(1)
    
    # Initialize client
    client = InfisicalClient(
        url=args.url,
        project_id=args.project_id,
        client_id=args.client_id if args.client_id else None,
        secret_key=args.secret_key if args.secret_key else None
    )
    
    print(f"Fetching secrets from {args.url}...")
    
    try:
        # Fetch all secrets
        secrets = client.get_secrets()
        
        if not secrets:
            print("Warning: No secrets found. Using default values.")
            
        print(f"Fetched {len(secrets)} secret(s)")
        
        # Generate docker-compose file
        generate_monitoring_compose(secrets, args.output)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

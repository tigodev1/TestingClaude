"""
Roblox Open Cloud DataStore API Client
Comprehensive implementation supporting v1 and v2 APIs
"""

import requests
import json
import hashlib
import base64
import time
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime


class RobloxDataStoreAPI:
    """Advanced Roblox Open Cloud DataStore API Client"""

    BASE_URL = "https://apis.roblox.com"

    def __init__(self, api_key: str, universe_id: str):
        self.api_key = api_key
        self.universe_id = universe_id
        self.session = requests.Session()
        self.session.headers.update({
            "x-api-key": api_key,
            "Content-Type": "application/json"
        })
        self.request_log = []
        self.rate_limit_remaining = 300
        self.rate_limit_reset = time.time() + 60

    def _log_request(self, method: str, url: str, status: int, response_time: float):
        """Log API requests for debugging"""
        self.request_log.append({
            "timestamp": datetime.now().isoformat(),
            "method": method,
            "url": url,
            "status": status,
            "response_time_ms": round(response_time * 1000, 2)
        })
        # Keep only last 100 requests
        if len(self.request_log) > 100:
            self.request_log = self.request_log[-100:]

    def _calculate_md5(self, data: Any) -> str:
        """Calculate MD5 hash for content integrity verification"""
        json_str = json.dumps(data, separators=(',', ':'))
        md5_hash = hashlib.md5(json_str.encode()).digest()
        return base64.b64encode(md5_hash).decode()

    def _handle_rate_limit(self):
        """Handle rate limiting - 300 requests per minute per universe"""
        current_time = time.time()
        if current_time >= self.rate_limit_reset:
            self.rate_limit_remaining = 300
            self.rate_limit_reset = current_time + 60

        if self.rate_limit_remaining <= 0:
            sleep_time = self.rate_limit_reset - current_time
            if sleep_time > 0:
                time.sleep(sleep_time)
                self.rate_limit_remaining = 300
                self.rate_limit_reset = time.time() + 60

        self.rate_limit_remaining -= 1

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None,
                      data: Optional[Any] = None, headers: Optional[Dict] = None) -> Tuple[Any, int]:
        """Make an API request with error handling and rate limiting"""
        self._handle_rate_limit()

        url = f"{self.BASE_URL}{endpoint}"
        req_headers = dict(self.session.headers)
        if headers:
            req_headers.update(headers)

        start_time = time.time()

        try:
            if method == "GET":
                response = self.session.get(url, params=params, headers=req_headers)
            elif method == "POST":
                if data is not None:
                    json_data = json.dumps(data, separators=(',', ':'))
                    req_headers["content-md5"] = self._calculate_md5(data)
                    response = self.session.post(url, params=params, data=json_data, headers=req_headers)
                else:
                    response = self.session.post(url, params=params, headers=req_headers)
            elif method == "DELETE":
                response = self.session.delete(url, params=params, headers=req_headers)
            elif method == "PATCH":
                if data is not None:
                    json_data = json.dumps(data, separators=(',', ':'))
                    response = self.session.patch(url, params=params, data=json_data, headers=req_headers)
                else:
                    response = self.session.patch(url, params=params, headers=req_headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response_time = time.time() - start_time
            self._log_request(method, url, response.status_code, response_time)

            # Parse response
            if response.status_code == 204:
                return None, response.status_code

            try:
                return response.json(), response.status_code
            except:
                return response.text, response.status_code

        except requests.exceptions.RequestException as e:
            response_time = time.time() - start_time
            self._log_request(method, url, 0, response_time)
            raise Exception(f"Request failed: {str(e)}")

    # ===== DATASTORE OPERATIONS =====

    def list_datastores(self, prefix: str = "", limit: int = 100, cursor: str = "") -> Dict:
        """List all datastores in the universe"""
        params = {"prefix": prefix, "limit": limit}
        if cursor:
            params["cursor"] = cursor

        data, status = self._make_request(
            "GET",
            f"/datastores/v1/universes/{self.universe_id}/standard-datastores",
            params=params
        )

        if status != 200:
            raise Exception(f"Failed to list datastores: {data}")
        return data

    def list_all_datastores(self) -> List[Dict]:
        """List all datastores with automatic pagination"""
        all_datastores = []
        cursor = ""

        while True:
            result = self.list_datastores(cursor=cursor)
            all_datastores.extend(result.get("datastores", []))
            cursor = result.get("nextPageCursor", "")
            if not cursor:
                break

        return all_datastores

    # ===== ENTRY OPERATIONS =====

    def list_entries(self, datastore_name: str, scope: str = "global",
                     prefix: str = "", limit: int = 100, cursor: str = "",
                     all_scopes: bool = False) -> Dict:
        """List entries in a datastore"""
        params = {
            "datastoreName": datastore_name,
            "scope": scope,
            "prefix": prefix,
            "limit": limit,
            "AllScopes": str(all_scopes).lower()
        }
        if cursor:
            params["cursor"] = cursor

        data, status = self._make_request(
            "GET",
            f"/datastores/v1/universes/{self.universe_id}/standard-datastores/datastore/entries",
            params=params
        )

        if status != 200:
            raise Exception(f"Failed to list entries: {data}")
        return data

    def list_all_entries(self, datastore_name: str, scope: str = "global",
                         prefix: str = "", all_scopes: bool = False) -> List[Dict]:
        """List all entries with automatic pagination"""
        all_entries = []
        cursor = ""

        while True:
            result = self.list_entries(
                datastore_name, scope, prefix, 100, cursor, all_scopes
            )
            all_entries.extend(result.get("keys", []))
            cursor = result.get("nextPageCursor", "")
            if not cursor:
                break

        return all_entries

    def get_entry(self, datastore_name: str, key: str, scope: str = "global") -> Tuple[Any, Dict]:
        """Get a single entry value and metadata"""
        params = {
            "datastoreName": datastore_name,
            "entryKey": key,
            "scope": scope
        }

        url = f"{self.BASE_URL}/datastores/v1/universes/{self.universe_id}/standard-datastores/datastore/entries/entry"

        self._handle_rate_limit()
        start_time = time.time()

        response = self.session.get(url, params=params)
        response_time = time.time() - start_time
        self._log_request("GET", url, response.status_code, response_time)

        if response.status_code != 200:
            raise Exception(f"Failed to get entry: {response.text}")

        # Extract metadata from headers
        metadata = {
            "version": response.headers.get("roblox-entry-version", ""),
            "created_time": response.headers.get("roblox-entry-created-time", ""),
            "updated_time": response.headers.get("roblox-entry-version-created-time", ""),
            "user_ids": json.loads(response.headers.get("roblox-entry-userids", "[]")),
            "attributes": json.loads(response.headers.get("roblox-entry-attributes", "{}"))
        }

        return response.json(), metadata

    def set_entry(self, datastore_name: str, key: str, value: Any,
                  scope: str = "global", user_ids: List[int] = None,
                  attributes: Dict = None, match_version: str = None,
                  exclusive_create: bool = False) -> Dict:
        """Set/update an entry value"""
        params = {
            "datastoreName": datastore_name,
            "entryKey": key,
            "scope": scope
        }

        if match_version:
            params["matchVersion"] = match_version
        if exclusive_create:
            params["exclusiveCreate"] = "true"

        headers = {}
        if user_ids:
            headers["roblox-entry-userids"] = json.dumps(user_ids)
        if attributes:
            headers["roblox-entry-attributes"] = json.dumps(attributes)

        url = f"{self.BASE_URL}/datastores/v1/universes/{self.universe_id}/standard-datastores/datastore/entries/entry"

        self._handle_rate_limit()
        start_time = time.time()

        json_data = json.dumps(value, separators=(',', ':'))
        headers["content-md5"] = self._calculate_md5(value)
        headers["x-api-key"] = self.api_key
        headers["Content-Type"] = "application/json"

        response = self.session.post(url, params=params, data=json_data, headers=headers)
        response_time = time.time() - start_time
        self._log_request("POST", url, response.status_code, response_time)

        if response.status_code != 200:
            raise Exception(f"Failed to set entry: {response.text}")

        return {
            "version": response.headers.get("roblox-entry-version", ""),
            "created_time": response.headers.get("roblox-entry-created-time", ""),
            "updated_time": response.headers.get("roblox-entry-version-created-time", "")
        }

    def delete_entry(self, datastore_name: str, key: str, scope: str = "global") -> bool:
        """Delete an entry (marks as deleted, can be recovered within ~30 days)"""
        params = {
            "datastoreName": datastore_name,
            "entryKey": key,
            "scope": scope
        }

        data, status = self._make_request(
            "DELETE",
            f"/datastores/v1/universes/{self.universe_id}/standard-datastores/datastore/entries/entry",
            params=params
        )

        if status != 204 and status != 200:
            raise Exception(f"Failed to delete entry: {data}")
        return True

    def increment_entry(self, datastore_name: str, key: str, increment_by: float,
                        scope: str = "global", user_ids: List[int] = None,
                        attributes: Dict = None) -> float:
        """Increment a numeric entry value"""
        params = {
            "datastoreName": datastore_name,
            "entryKey": key,
            "scope": scope,
            "incrementBy": increment_by
        }

        headers = {"content-length": "0"}
        if user_ids:
            headers["roblox-entry-userids"] = json.dumps(user_ids)
        if attributes:
            headers["roblox-entry-attributes"] = json.dumps(attributes)

        url = f"{self.BASE_URL}/datastores/v1/universes/{self.universe_id}/standard-datastores/datastore/entries/entry/increment"

        self._handle_rate_limit()
        start_time = time.time()

        headers["x-api-key"] = self.api_key
        response = self.session.post(url, params=params, headers=headers)
        response_time = time.time() - start_time
        self._log_request("POST", url, response.status_code, response_time)

        if response.status_code != 200:
            raise Exception(f"Failed to increment entry: {response.text}")

        return response.json()

    # ===== VERSION OPERATIONS =====

    def list_versions(self, datastore_name: str, key: str, scope: str = "global",
                      sort_order: str = "Descending", limit: int = 100,
                      cursor: str = "", start_time: str = "", end_time: str = "") -> Dict:
        """List version history for an entry"""
        params = {
            "datastoreName": datastore_name,
            "entryKey": key,
            "scope": scope,
            "sortOrder": sort_order,
            "limit": limit
        }
        if cursor:
            params["cursor"] = cursor
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data, status = self._make_request(
            "GET",
            f"/datastores/v1/universes/{self.universe_id}/standard-datastores/datastore/entries/entry/versions",
            params=params
        )

        if status != 200:
            raise Exception(f"Failed to list versions: {data}")
        return data

    def get_version(self, datastore_name: str, key: str, version: str,
                    scope: str = "global") -> Any:
        """Get a specific version of an entry"""
        params = {
            "datastoreName": datastore_name,
            "entryKey": key,
            "scope": scope,
            "versionId": version
        }

        data, status = self._make_request(
            "GET",
            f"/datastores/v1/universes/{self.universe_id}/standard-datastores/datastore/entries/entry/versions/version",
            params=params
        )

        if status != 200:
            raise Exception(f"Failed to get version: {data}")
        return data

    def list_all_versions(self, datastore_name: str, key: str,
                          scope: str = "global") -> List[Dict]:
        """List all versions with automatic pagination"""
        all_versions = []
        cursor = ""

        while True:
            result = self.list_versions(datastore_name, key, scope, cursor=cursor)
            all_versions.extend(result.get("versions", []))
            cursor = result.get("nextPageCursor", "")
            if not cursor:
                break

        return all_versions

    # ===== BULK OPERATIONS =====

    def bulk_get_entries(self, datastore_name: str, keys: List[str],
                         scope: str = "global") -> Dict[str, Any]:
        """Get multiple entries at once"""
        results = {}
        for key in keys:
            try:
                value, metadata = self.get_entry(datastore_name, key, scope)
                results[key] = {
                    "value": value,
                    "metadata": metadata,
                    "error": None
                }
            except Exception as e:
                results[key] = {
                    "value": None,
                    "metadata": None,
                    "error": str(e)
                }
        return results

    def bulk_delete_entries(self, datastore_name: str, keys: List[str],
                            scope: str = "global") -> Dict[str, bool]:
        """Delete multiple entries at once"""
        results = {}
        for key in keys:
            try:
                self.delete_entry(datastore_name, key, scope)
                results[key] = True
            except Exception as e:
                results[key] = False
        return results

    def export_datastore(self, datastore_name: str, scope: str = "global",
                         include_metadata: bool = True) -> List[Dict]:
        """Export entire datastore to JSON-compatible format"""
        entries = self.list_all_entries(datastore_name, scope)
        export_data = []

        for entry in entries:
            key = entry.get("key", "")
            try:
                value, metadata = self.get_entry(datastore_name, key, scope)
                export_entry = {
                    "key": key,
                    "scope": scope,
                    "value": value
                }
                if include_metadata:
                    export_entry["metadata"] = metadata
                export_data.append(export_entry)
            except Exception as e:
                export_data.append({
                    "key": key,
                    "scope": scope,
                    "value": None,
                    "error": str(e)
                })

        return export_data

    def import_datastore(self, datastore_name: str, data: List[Dict],
                         scope: str = "global", overwrite: bool = False) -> Dict:
        """Import data into datastore"""
        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for entry in data:
            key = entry.get("key", "")
            value = entry.get("value")
            user_ids = entry.get("metadata", {}).get("user_ids", [])
            attributes = entry.get("metadata", {}).get("attributes", {})

            try:
                self.set_entry(
                    datastore_name, key, value, scope,
                    user_ids=user_ids if user_ids else None,
                    attributes=attributes if attributes else None,
                    exclusive_create=not overwrite
                )
                results["success"] += 1
            except Exception as e:
                if "EntryAlreadyExists" in str(e) and not overwrite:
                    results["skipped"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({"key": key, "error": str(e)})

        return results

    def get_request_log(self) -> List[Dict]:
        """Get the request log for debugging"""
        return self.request_log

    def get_rate_limit_status(self) -> Dict:
        """Get current rate limit status"""
        return {
            "remaining": self.rate_limit_remaining,
            "reset_in_seconds": max(0, self.rate_limit_reset - time.time())
        }


class OrderedDataStoreAPI(RobloxDataStoreAPI):
    """API client for Ordered DataStores"""

    def list_ordered_entries(self, datastore_name: str, scope: str = "global",
                             ascending: bool = True, limit: int = 100,
                             cursor: str = "", filter_expr: str = "") -> Dict:
        """List entries in an ordered datastore"""
        params = {
            "max_page_size": limit,
            "order_by": "value" if ascending else "value desc"
        }
        if cursor:
            params["page_token"] = cursor
        if filter_expr:
            params["filter"] = filter_expr

        data, status = self._make_request(
            "GET",
            f"/ordered-data-stores/v1/universes/{self.universe_id}/orderedDataStores/{datastore_name}/scopes/{scope}/entries"
        )

        if status != 200:
            raise Exception(f"Failed to list ordered entries: {data}")
        return data

    def create_ordered_entry(self, datastore_name: str, key: str, value: int,
                             scope: str = "global") -> Dict:
        """Create an entry in ordered datastore"""
        data = {"value": value}

        result, status = self._make_request(
            "POST",
            f"/ordered-data-stores/v1/universes/{self.universe_id}/orderedDataStores/{datastore_name}/scopes/{scope}/entries",
            params={"id": key},
            data=data
        )

        if status != 200:
            raise Exception(f"Failed to create ordered entry: {result}")
        return result

    def update_ordered_entry(self, datastore_name: str, key: str, value: int,
                             scope: str = "global") -> Dict:
        """Update an entry in ordered datastore"""
        data = {"value": value}

        result, status = self._make_request(
            "PATCH",
            f"/ordered-data-stores/v1/universes/{self.universe_id}/orderedDataStores/{datastore_name}/scopes/{scope}/entries/{key}",
            data=data
        )

        if status != 200:
            raise Exception(f"Failed to update ordered entry: {result}")
        return result

    def increment_ordered_entry(self, datastore_name: str, key: str,
                                increment_by: int, scope: str = "global") -> Dict:
        """Increment an ordered datastore entry"""
        data = {"amount": increment_by}

        result, status = self._make_request(
            "POST",
            f"/ordered-data-stores/v1/universes/{self.universe_id}/orderedDataStores/{datastore_name}/scopes/{scope}/entries/{key}:increment",
            data=data
        )

        if status != 200:
            raise Exception(f"Failed to increment ordered entry: {result}")
        return result

    def delete_ordered_entry(self, datastore_name: str, key: str,
                             scope: str = "global") -> bool:
        """Delete an ordered datastore entry"""
        result, status = self._make_request(
            "DELETE",
            f"/ordered-data-stores/v1/universes/{self.universe_id}/orderedDataStores/{datastore_name}/scopes/{scope}/entries/{key}"
        )

        if status != 204 and status != 200:
            raise Exception(f"Failed to delete ordered entry: {result}")
        return True

"""Kommo API service for handling REST API requests to Kommo CRM."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import requests
from requests.exceptions import HTTPError, RequestException, Timeout

logger = logging.getLogger(__name__)


class KommoAPIError(Exception):
    """Base exception for Kommo API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class KommoRateLimitError(KommoAPIError):
    """Exception raised when API rate limit is exceeded."""
    pass


class KommoAuthenticationError(KommoAPIError):
    """Exception raised when authentication fails."""
    pass


class KommoAPIService:
    """Service class for Kommo CRM API operations."""
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        subdomain: str,
        access_token: str,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Kommo API service.
        
        Args:
            client_id: Kommo OAuth client ID
            client_secret: Kommo OAuth client secret
            subdomain: Kommo account subdomain
            access_token: Kommo API access token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.subdomain = subdomain
        self.access_token = access_token
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Build base URLs for different API versions
        self.base_url = f"https://{subdomain}.kommo.com/api/v4/"
        self.base_url_v2 = f"https://{subdomain}.kommo.com/api/v2/"
        
        # Initialize session
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        logger.info(f"Initialized Kommo API service for subdomain: {subdomain}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_count: int = 0,
        api_version: str = 'v4',
    ) -> Dict[str, Any]:
        """
        Make a request to the Kommo API.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            data: Request body data (dict or list of dicts)
            headers: Additional headers
            retry_count: Current retry attempt
            api_version: API version ('v2' or 'v4', default: 'v4')
            
        Returns:
            JSON response data
            
        Raises:
            KommoAPIError: For API-related errors
            KommoRateLimitError: When rate limit is exceeded
            KommoAuthenticationError: When authentication fails
        """
        # Choose the appropriate base URL based on API version
        base_url = self.base_url_v2 if api_version == 'v2' else self.base_url
        url = urljoin(base_url, endpoint.lstrip('/'))
        
        # Prepare request arguments
        request_kwargs: Dict[str, Any] = {
            'timeout': self.timeout,
        }
        
        if params is not None:
            request_kwargs['params'] = params
        if headers is not None:
            request_kwargs['headers'] = headers
        if data is not None:
            request_kwargs['json'] = data
        
        try:
            logger.debug(f"Making {method} request to {url}")
            response = self.session.request(method, url, **request_kwargs)
            
            # Handle rate limiting
            if response.status_code == 429:
                if retry_count < self.max_retries:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds")
                    time.sleep(retry_after)
                    return self._make_request(method, endpoint, params, data, headers, retry_count + 1, api_version)
                else:
                    raise KommoRateLimitError(
                        "Rate limit exceeded and max retries reached",
                        status_code=response.status_code
                    )
            
            # Handle authentication errors
            if response.status_code == 401:
                raise KommoAuthenticationError(
                    "Authentication failed. Check your access token",
                    status_code=response.status_code
                )
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            # Parse JSON response
            try:
                json_response = response.json()
                return json_response  # type: ignore[no-any-return]
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                return {'raw_response': response.text}
        
        except Timeout as e:
            error_msg = f"Request timeout after {self.timeout} seconds"
            logger.error(error_msg)
            if retry_count < self.max_retries:
                logger.info(f"Retrying request ({retry_count + 1}/{self.max_retries})")
                return self._make_request(method, endpoint, params, data, headers, retry_count + 1, api_version)
            raise KommoAPIError(error_msg) from e
        
        except HTTPError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            
            try:
                error_data = e.response.json()
            except json.JSONDecodeError:
                error_data = {'raw_response': e.response.text}
            
            raise KommoAPIError(
                error_msg,
                status_code=e.response.status_code,
                response_data=error_data
            ) from e
        
        except RequestException as e:
            error_msg = f"Request failed: {str(e)}"
            logger.error(error_msg)
            if retry_count < self.max_retries:
                logger.info(f"Retrying request ({retry_count + 1}/{self.max_retries})")
                return self._make_request(method, endpoint, params, data, headers, retry_count + 1, api_version)
            raise KommoAPIError(error_msg) from e
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a GET request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers
            
        Returns:
            JSON response data
        """
        return self._make_request('GET', endpoint, params=params, headers=headers)
    
    def post(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a POST request.
        
        Args:
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            JSON response data
        """
        return self._make_request('POST', endpoint, params=params, data=data, headers=headers)
    
    def patch(
        self,
        endpoint: str,
        data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a PATCH request.
        
        Args:
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            JSON response data
        """
        return self._make_request('PATCH', endpoint, params=params, data=data, headers=headers)
    
    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Make a DELETE request.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            headers: Additional headers
            
        Returns:
            JSON response data
        """
        return self._make_request('DELETE', endpoint, params=params, headers=headers)
    
    # Convenience methods for common Kommo API operations
    
    def get_leads(
        self,
        page: int = 1,
        limit: int = 250,
        query: Optional[str] = None,
        responsible_user_id: Optional[int] = None,
        status_id: Optional[int] = None,
        pipeline_id: Optional[int] = None,
        with_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get leads from Kommo.
        
        Args:
            page: Page number (default: 1)
            limit: Number of records per page (max: 250)
            query: Search query
            responsible_user_id: Filter by responsible user ID
            status_id: Filter by status ID
            pipeline_id: Filter by pipeline ID
            with_fields: Additional fields to include
            
        Returns:
            JSON response with leads data
        """
        params: Dict[str, Any] = {
            'page': page,
            'limit': min(limit, 250),  # Kommo API limit
        }
        
        if query:
            params['query'] = query
        if responsible_user_id:
            params['filter[responsible_user_id]'] = responsible_user_id
        if status_id:
            params['filter[statuses][0][status_id]'] = status_id
        if pipeline_id:
            params['filter[statuses][0][pipeline_id]'] = pipeline_id
        if with_fields:
            params['with'] = ','.join(with_fields)
        
        return self.get('leads', params=params)
    
    def get_lead(self, lead_id: int, with_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get a specific lead by ID.
        
        Args:
            lead_id: Lead ID
            with_fields: Additional fields to include
            
        Returns:
            JSON response with lead data
        """
        params: Dict[str, Any] = {}
        if with_fields:
            params['with'] = ','.join(with_fields)
        
        return self.get(f'leads/{lead_id}', params=params)
    
    def create_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new lead.
        
        Args:
            lead_data: Lead data
            
        Returns:
            JSON response with created lead data
        """
        return self.post('leads', data=lead_data)
    
    def update_lead(self, lead_id: int, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing lead.
        
        Args:
            lead_id: Lead ID
            lead_data: Updated lead data
            
        Returns:
            JSON response with updated lead data
        """
        return self.patch(f'leads/{lead_id}', data=lead_data)
    
    def update_lead_custom_fields(
        self, 
        lead_id: int, 
        custom_fields: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update custom fields values for a specific lead.
        
        Args:
            lead_id: Lead ID to update
            custom_fields: List of custom field dictionaries. Each dict should contain:
                - field_id: Custom field ID (required)
                - field_name: Custom field name (optional)
                - field_code: Custom field code (optional)
                - field_type: Custom field type (optional)
                - values: List of values, each as a dict with 'value' key (required)
                
        Returns:
            JSON response with updated lead data
            
        Raises:
            ValueError: If custom_fields is empty or invalid
            
        Example:
            custom_fields = [
                {
                    "field_id": 1069656,
                    "field_name": "Custom Message",
                    "field_type": "textarea", 
                    "values": [{"value": "Hello World"}]
                }
            ]
            result = service.update_lead_custom_fields(12345, custom_fields)
        """
        if not custom_fields:
            raise ValueError("custom_fields list cannot be empty")
        
        if not isinstance(custom_fields, list):
            raise ValueError("custom_fields must be a list")
        
        # Validate each custom field has required fields
        for i, field in enumerate(custom_fields):
            if not isinstance(field, dict):
                raise ValueError(f"Custom field {i} must be a dictionary")
            
            if 'field_id' not in field:
                raise ValueError(f"Custom field {i} missing required 'field_id'")
            
            if 'values' not in field:
                raise ValueError(f"Custom field {i} missing required 'values'")
            
            if not isinstance(field['values'], list):
                raise ValueError(f"Custom field {i} 'values' must be a list")
        
        # Prepare the payload
        lead_data = {
            'custom_fields_values': custom_fields
        }
        
        logger.debug(f"Updating custom fields for lead {lead_id}")
        result = self.patch(f'leads/{lead_id}', data=lead_data)
        logger.info(f"Successfully updated custom fields for lead {lead_id}")
        
        return result
    
    def get_contacts(
        self,
        page: int = 1,
        limit: int = 250,
        query: Optional[str] = None,
        responsible_user_id: Optional[int] = None,
        with_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get contacts from Kommo.
        
        Args:
            page: Page number (default: 1)
            limit: Number of records per page (max: 250)
            query: Search query
            responsible_user_id: Filter by responsible user ID
            with_fields: Additional fields to include
            
        Returns:
            JSON response with contacts data
        """
        params: Dict[str, Any] = {
            'page': page,
            'limit': min(limit, 250),
        }
        
        if query:
            params['query'] = query
        if responsible_user_id:
            params['filter[responsible_user_id]'] = responsible_user_id
        if with_fields:
            params['with'] = ','.join(with_fields)
        
        return self.get('contacts', params=params)
    
    def get_contact(self, contact_id: int, with_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get a specific contact by ID.
        
        Args:
            contact_id: Contact ID
            with_fields: Additional fields to include
            
        Returns:
            JSON response with contact data
        """
        params: Dict[str, Any] = {}
        if with_fields:
            params['with'] = ','.join(with_fields)
        
        return self.get(f'contacts/{contact_id}', params=params)
    
    def create_contact(self, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new contact.
        
        Args:
            contact_data: Contact data
            
        Returns:
            JSON response with created contact data
        """
        return self.post('contacts', data=contact_data)
    
    def update_contact(self, contact_id: int, contact_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing contact.
        
        Args:
            contact_id: Contact ID
            contact_data: Updated contact data
            
        Returns:
            JSON response with updated contact data
        """
        return self.patch(f'contacts/{contact_id}', data=contact_data)
    
    def get_companies(
        self,
        page: int = 1,
        limit: int = 250,
        query: Optional[str] = None,
        responsible_user_id: Optional[int] = None,
        with_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get companies from Kommo.
        
        Args:
            page: Page number (default: 1)
            limit: Number of records per page (max: 250)
            query: Search query
            responsible_user_id: Filter by responsible user ID
            with_fields: Additional fields to include
            
        Returns:
            JSON response with companies data
        """
        params: Dict[str, Any] = {
            'page': page,
            'limit': min(limit, 250),
        }
        
        if query:
            params['query'] = query
        if responsible_user_id:
            params['filter[responsible_user_id]'] = responsible_user_id
        if with_fields:
            params['with'] = ','.join(with_fields)
        
        return self.get('companies', params=params)
    
    def get_pipelines(self) -> Dict[str, Any]:
        """
        Get all pipelines.
        
        Returns:
            JSON response with pipelines data
        """
        return self.get('leads/pipelines')
    
    def get_custom_fields(self, entity_type: str = 'leads') -> Dict[str, Any]:
        """
        Get custom fields for an entity type.
        
        Args:
            entity_type: Entity type (leads, contacts, companies)
            
        Returns:
            JSON response with custom fields data
        """
        return self.get(f'{entity_type}/custom_fields')
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            JSON response with account data
        """
        return self.get('account')
    
    @staticmethod
    def get_entity_type_code(entity_name: str) -> str:
        """
        Convert entity name to Kommo API entity type code.
        
        Args:
            entity_name: Entity name ('contact' or 'lead')
            
        Returns:
            Entity type code ('1' for contact, '2' for lead)
            
        Raises:
            ValueError: If entity_name is not supported
        """
        entity_mapping = {
            'contact': '1',
            'lead': '2',
            'contacts': '1',  # Also accept plural
            'leads': '2',     # Also accept plural
        }
        
        entity_name_lower = entity_name.lower()
        if entity_name_lower not in entity_mapping:
            raise ValueError(f"Invalid entity_name '{entity_name}'. Must be 'contact', 'lead', 'contacts', or 'leads'")
        
        return entity_mapping[entity_name_lower]
    
    def launch_salesbot(
        self,
        bot_id: int,
        entity_id: int,
        entity_type: str = '2',
    ) -> Dict[str, Any]:
        """
        Launch a salesbot for a specific entity.
        
        Args:
            bot_id: Salesbot ID (can be obtained from Salesbots list in Kommo interface)
            entity_id: ID of the entity to run the bot against (lead or contact)
            entity_type: Type of entity ('1' for contact, '2' for lead). Default is '2' (lead)
            
        Returns:
            JSON response with salesbot launch result
            
        Raises:
            KommoAPIError: For API-related errors
            ValueError: If entity_type is not '1' or '2'
            
        Note:
            - Maximum 100 bots can be launched at a time
            - Bot ID can be found in Salesbots list using browser dev tools
            - Uses v2 API endpoint specifically for salesbot operations
            - entity_type: '1' = contact, '2' = lead (as per Kommo API specification)
            - API expects an array of salesbot launch requests
        """
        # Validate entity_type
        if entity_type not in ('1', '2'):
            raise ValueError(f"Invalid entity_type '{entity_type}'. Must be '1' (contact) or '2' (lead)")
        
        # Prepare request data as an array (API expects array format)
        data = [
            {
                'bot_id': bot_id,
                'entity_id': entity_id,
                'entity_type': entity_type,
            }
        ]
        
        entity_type_name = 'contact' if entity_type == '1' else 'lead'
        logger.debug(f"Launching salesbot {bot_id} for {entity_type_name} (type {entity_type}) with ID {entity_id}")
        
        # Use v2 API for salesbot operations
        result = self._make_request('POST', 'salesbot/run', data=data, api_version='v2')
        
        logger.info(f"Successfully launched salesbot {bot_id} for {entity_type_name} {entity_id}")
        return result
    
    def launch_multiple_salesbots(
        self,
        bot_requests: List[Dict[str, Union[int, str]]],
    ) -> Dict[str, Any]:
        """
        Launch multiple salesbots in a single API call.
        
        Args:
            bot_requests: List of bot launch requests. Each request should be a dict with:
                - bot_id: Salesbot ID
                - entity_id: Entity ID (lead or contact)
                - entity_type: '1' for contact, '2' for lead
                
        Returns:
            JSON response with salesbot launch results
            
        Raises:
            KommoAPIError: For API-related errors
            ValueError: If any entity_type is not '1' or '2', or if too many requests
            
        Example:
            requests = [
                {'bot_id': 12345, 'entity_id': 67890, 'entity_type': '2'},
                {'bot_id': 12346, 'entity_id': 67891, 'entity_type': '1'},
            ]
            result = service.launch_multiple_salesbots(requests)
        """
        if len(bot_requests) > 100:
            raise ValueError("Maximum 100 salesbot launch requests allowed per API call")
        
        if not bot_requests:
            raise ValueError("At least one bot request is required")
        
        # Validate all requests
        validated_requests = []
        for i, request in enumerate(bot_requests):
            if not isinstance(request, dict):
                raise ValueError(f"Request {i} must be a dictionary")
            
            required_fields = ['bot_id', 'entity_id', 'entity_type']
            for field in required_fields:
                if field not in request:
                    raise ValueError(f"Request {i} missing required field: {field}")
            
            entity_type = str(request['entity_type'])
            if entity_type not in ('1', '2'):
                raise ValueError(f"Request {i} has invalid entity_type '{entity_type}'. Must be '1' or '2'")
            
            validated_requests.append({
                'bot_id': int(request['bot_id']),
                'entity_id': int(request['entity_id']),
                'entity_type': entity_type,
            })
        
        logger.debug(f"Launching {len(validated_requests)} salesbots")
        
        # Use v2 API for salesbot operations
        result = self._make_request('POST', 'salesbot/run', data=validated_requests, api_version='v2')
        
        logger.info(f"Successfully launched {len(validated_requests)} salesbots")
        return result
    
    def test_connection(self) -> bool:
        """
        Test the API connection by fetching account info.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.get_account_info()
            if response and 'id' in response:
                logger.info("Kommo API connection test successful")
                return True
            else:
                logger.error("Kommo API connection test failed: Invalid response")
                return False
        except Exception as e:
            logger.error(f"Kommo API connection test failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()
            logger.debug("Closed Kommo API session")
    
    def __enter__(self) -> KommoAPIService:
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
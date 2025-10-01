"""
BAIS Platform - Website Intelligence Extractor

This module analyzes business websites to extract structured information
that can be used to generate BAIS-compliant schemas and demo applications.
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
import dateutil.parser
from PIL import Image
import io
import base64

from pydantic import BaseModel, Field, validator


class BusinessCategory(str, Enum):
    """Business category classification"""
    HOTEL = "hotel"
    RESTAURANT = "restaurant"
    RETAIL = "retail"
    SERVICE = "service"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    TRANSPORTATION = "transportation"
    REAL_ESTATE = "real_estate"
    PROFESSIONAL_SERVICES = "professional_services"


class ServiceType(str, Enum):
    """Service type classification"""
    BOOKING = "booking"
    PURCHASE = "purchase"
    CONSULTATION = "consultation"
    SUBSCRIPTION = "subscription"
    RENTAL = "rental"
    DELIVERY = "delivery"
    RESERVATION = "reservation"


@dataclass
class ContactInfo:
    """Extracted contact information"""
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    social_media: Dict[str, str] = None
    
    def __post_init__(self):
        if self.social_media is None:
            self.social_media = {}


@dataclass
class OperationalHours:
    """Business operational hours"""
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class PricingInfo:
    """Pricing information"""
    currency: str = "USD"
    price_range: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    pricing_model: Optional[str] = None  # "per_night", "per_person", "fixed", etc.


@dataclass
class Service:
    """Extracted service information"""
    id: str
    name: str
    description: str
    category: str
    service_type: ServiceType
    price: Optional[float] = None
    currency: str = "USD"
    availability: Optional[str] = None
    requirements: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MediaContent:
    """Media content information"""
    images: List[str] = None
    videos: List[str] = None
    logos: List[str] = None
    
    def __post_init__(self):
        if self.images is None:
            self.images = []
        if self.videos is None:
            self.videos = []
        if self.logos is None:
            self.logos = []


@dataclass
class WebContent:
    """Structured web content"""
    url: str
    title: str
    text: str
    navigation: List[Dict[str, str]]
    structured_data: Dict[str, Any]
    meta_tags: Dict[str, str]
    forms: List[Dict[str, Any]]
    links: List[str]


@dataclass
class BusinessIntelligence:
    """Complete business intelligence extracted from website"""
    business_name: str
    business_type: BusinessCategory
    description: str
    services: List[Service]
    contact_info: ContactInfo
    operational_hours: Optional[OperationalHours]
    pricing_info: PricingInfo
    media_content: MediaContent
    location: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    extracted_at: datetime
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class WebsiteAnalyzer:
    """
    Website Intelligence Extractor for BAIS Demo Generation
    
    Analyzes business websites to extract structured information
    for generating BAIS-compliant schemas and demonstrations.
    """
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.user_agent = "BAIS-WebsiteAnalyzer/1.0 (Business Intelligence Extraction)"
        
        # Common business type keywords for classification
        self.business_keywords = {
            BusinessCategory.HOTEL: [
                "hotel", "resort", "inn", "lodge", "accommodation", "suite", "room", "stay",
                "booking", "reservation", "check-in", "check-out", "guest", "amenities"
            ],
            BusinessCategory.RESTAURANT: [
                "restaurant", "cafe", "bistro", "diner", "eatery", "kitchen", "chef",
                "menu", "dining", "food", "cuisine", "meal", "order", "delivery", "takeout"
            ],
            BusinessCategory.RETAIL: [
                "shop", "store", "boutique", "retail", "product", "inventory", "catalog",
                "purchase", "buy", "cart", "checkout", "shipping", "merchandise"
            ],
            BusinessCategory.SERVICE: [
                "service", "consultation", "appointment", "booking", "schedule", "professional",
                "expert", "specialist", "therapy", "treatment", "session"
            ],
            BusinessCategory.HEALTHCARE: [
                "healthcare", "medical", "doctor", "clinic", "hospital", "therapy",
                "treatment", "appointment", "patient", "health", "wellness"
            ]
        }
    
    async def analyze_business_website(self, url: str) -> BusinessIntelligence:
        """
        Extract business information from website
        
        Args:
            url: Website URL to analyze
            
        Returns:
            BusinessIntelligence: Extracted business information
        """
        try:
            # Scrape website content
            content = await self._scrape_website(url)
            
            # Extract business intelligence
            intelligence = BusinessIntelligence(
                business_name=self._extract_business_name(content),
                business_type=self._classify_business_type(content),
                description=self._extract_description(content),
                services=self._extract_services(content),
                contact_info=self._extract_contact_info(content),
                operational_hours=self._extract_operational_hours(content),
                pricing_info=self._extract_pricing_info(content),
                media_content=self._extract_media_content(content),
                location=self._extract_location(content),
                metadata=self._extract_metadata(content),
                extracted_at=datetime.utcnow()
            )
            
            return intelligence
            
        except Exception as e:
            raise Exception(f"Website analysis failed: {str(e)}")
    
    async def _scrape_website(self, url: str) -> WebContent:
        """Scrape website content"""
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            async with self.session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract structured data
                structured_data = self._extract_structured_data(soup)
                
                # Extract navigation
                navigation = self._extract_navigation(soup)
                
                # Extract meta tags
                meta_tags = self._extract_meta_tags(soup)
                
                # Extract forms
                forms = self._extract_forms(soup)
                
                # Extract links
                links = self._extract_links(soup, url)
                
                return WebContent(
                    url=url,
                    title=soup.title.string if soup.title else "",
                    text=soup.get_text(separator=' ', strip=True),
                    navigation=navigation,
                    structured_data=structured_data,
                    meta_tags=meta_tags,
                    forms=forms,
                    links=links
                )
                
        except Exception as e:
            raise Exception(f"Website scraping failed: {str(e)}")
    
    def _extract_business_name(self, content: WebContent) -> str:
        """Extract business name from content"""
        # Try structured data first
        if 'name' in content.structured_data:
            return content.structured_data['name']
        
        # Try meta tags
        if 'og:site_name' in content.meta_tags:
            return content.meta_tags['og:site_name']
        
        # Try title tag
        if content.title:
            # Remove common suffixes
            title = content.title
            for suffix in [' - Home', ' - Official Site', ' | Home', ' | Official']:
                title = title.replace(suffix, '')
            return title.strip()
        
        # Fallback to URL domain
        parsed = urlparse(content.url)
        domain = parsed.netloc.replace('www.', '').split('.')[0]
        return domain.replace('-', ' ').replace('_', ' ').title()
    
    def _classify_business_type(self, content: WebContent) -> BusinessCategory:
        """Classify business type using ML-like keyword analysis"""
        text = content.text.lower()
        
        # Score each business type
        scores = {}
        for category, keywords in self.business_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text)
            scores[category] = score
        
        # Return highest scoring category
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        # Default classification
        return BusinessCategory.SERVICE
    
    def _extract_description(self, content: WebContent) -> str:
        """Extract business description"""
        # Try structured data
        if 'description' in content.structured_data:
            return content.structured_data['description']
        
        # Try meta description
        if 'description' in content.meta_tags:
            return content.meta_tags['description']
        
        # Try og:description
        if 'og:description' in content.meta_tags:
            return content.meta_tags['og:description']
        
        # Extract from first paragraph
        paragraphs = content.text.split('\n')
        for paragraph in paragraphs:
            if len(paragraph.strip()) > 50:
                return paragraph.strip()[:500]  # Limit length
        
        return "Business description not available"
    
    def _extract_services(self, content: WebContent) -> List[Service]:
        """Extract services from website content"""
        services = []
        
        # Extract from structured data
        if 'offers' in content.structured_data:
            offers = content.structured_data['offers']
            if isinstance(offers, list):
                for i, offer in enumerate(offers):
                    service = Service(
                        id=f"service_{i}",
                        name=offer.get('name', f"Service {i+1}"),
                        description=offer.get('description', ''),
                        category=offer.get('category', 'general'),
                        service_type=self._classify_service_type(offer),
                        price=offer.get('price'),
                        currency=offer.get('priceCurrency', 'USD'),
                        metadata=offer
                    )
                    services.append(service)
        
        # Extract from navigation menus
        for nav_item in content.navigation:
            if any(keyword in nav_item['text'].lower() for keyword in 
                   ['services', 'menu', 'products', 'offerings', 'book', 'reserve']):
                # This might be a service category
                service = Service(
                    id=f"nav_service_{len(services)}",
                    name=nav_item['text'],
                    description=f"Service: {nav_item['text']}",
                    category="general",
                    service_type=ServiceType.BOOKING,
                    metadata={'source': 'navigation', 'url': nav_item['url']}
                )
                services.append(service)
        
        # Extract from forms (booking/reservation forms)
        for form in content.forms:
            if any(keyword in form.get('action', '').lower() for keyword in 
                   ['book', 'reserve', 'appointment', 'contact']):
                service = Service(
                    id=f"form_service_{len(services)}",
                    name=form.get('name', 'Booking Service'),
                    description="Service available for booking",
                    category="booking",
                    service_type=ServiceType.BOOKING,
                    metadata={'source': 'form', 'action': form.get('action')}
                )
                services.append(service)
        
        # If no services found, create a default one
        if not services:
            services.append(Service(
                id="default_service",
                name="General Service",
                description="General business service",
                category="general",
                service_type=ServiceType.BOOKING
            ))
        
        return services
    
    def _extract_contact_info(self, content: WebContent) -> ContactInfo:
        """Extract contact information"""
        contact = ContactInfo()
        
        # Extract from structured data
        if 'telephone' in content.structured_data:
            contact.phone = content.structured_data['telephone']
        
        if 'email' in content.structured_data:
            contact.email = content.structured_data['email']
        
        # Extract from text using regex
        phone_pattern = r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'
        phone_match = re.search(phone_pattern, content.text)
        if phone_match and not contact.phone:
            contact.phone = phone_match.group(0)
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, content.text)
        if email_match and not contact.email:
            contact.email = email_match.group(0)
        
        # Extract address from structured data
        if 'address' in content.structured_data:
            address_data = content.structured_data['address']
            if isinstance(address_data, dict):
                address_parts = []
                for field in ['streetAddress', 'addressLocality', 'addressRegion', 'postalCode']:
                    if field in address_data:
                        address_parts.append(address_data[field])
                if address_parts:
                    contact.address = ', '.join(address_parts)
        
        # Extract social media links
        for link in content.links:
            if 'facebook.com' in link:
                contact.social_media['facebook'] = link
            elif 'twitter.com' in link or 'x.com' in link:
                contact.social_media['twitter'] = link
            elif 'instagram.com' in link:
                contact.social_media['instagram'] = link
            elif 'linkedin.com' in link:
                contact.social_media['linkedin'] = link
        
        return contact
    
    def _extract_operational_hours(self, content: WebContent) -> Optional[OperationalHours]:
        """Extract operational hours"""
        # Try structured data
        if 'openingHours' in content.structured_data:
            hours_data = content.structured_data['openingHours']
            if isinstance(hours_data, list):
                hours = OperationalHours()
                for hour_entry in hours_data:
                    # Parse opening hours format (e.g., "Mo-Fr 09:00-17:00")
                    # This is a simplified parser
                    if 'Mo' in hour_entry:
                        hours.monday = hour_entry
                    elif 'Tu' in hour_entry:
                        hours.tuesday = hour_entry
                    elif 'We' in hour_entry:
                        hours.wednesday = hour_entry
                    elif 'Th' in hour_entry:
                        hours.thursday = hour_entry
                    elif 'Fr' in hour_entry:
                        hours.friday = hour_entry
                    elif 'Sa' in hour_entry:
                        hours.saturday = hour_entry
                    elif 'Su' in hour_entry:
                        hours.sunday = hour_entry
                return hours
        
        return None
    
    def _extract_pricing_info(self, content: WebContent) -> PricingInfo:
        """Extract pricing information"""
        pricing = PricingInfo()
        
        # Look for price patterns in text
        price_pattern = r'\$(\d+(?:\.\d{2})?)'
        prices = re.findall(price_pattern, content.text)
        
        if prices:
            prices_float = [float(p) for p in prices]
            pricing.min_price = min(prices_float)
            pricing.max_price = max(prices_float)
            
            if pricing.min_price == pricing.max_price:
                pricing.pricing_model = "fixed"
            else:
                pricing.pricing_model = "variable"
        
        # Look for price range indicators
        if 'from $' in content.text.lower() or 'starting at $' in content.text.lower():
            pricing.pricing_model = "range"
        
        return pricing
    
    def _extract_media_content(self, content: WebContent) -> MediaContent:
        """Extract media content URLs"""
        media = MediaContent()
        
        # Extract images from structured data
        if 'image' in content.structured_data:
            images = content.structured_data['image']
            if isinstance(images, list):
                media.images = images
            else:
                media.images = [images]
        
        # Extract from meta tags
        if 'og:image' in content.meta_tags:
            media.images.append(content.meta_tags['og:image'])
        
        return media
    
    def _extract_location(self, content: WebContent) -> Optional[Dict[str, Any]]:
        """Extract location information"""
        location = {}
        
        # Extract from structured data
        if 'geo' in content.structured_data:
            geo = content.structured_data['geo']
            if isinstance(geo, dict):
                location.update(geo)
        
        if 'address' in content.structured_data:
            location['address'] = content.structured_data['address']
        
        return location if location else None
    
    def _extract_metadata(self, content: WebContent) -> Dict[str, Any]:
        """Extract additional metadata"""
        metadata = {
            'url': content.url,
            'title': content.title,
            'meta_tags': content.meta_tags,
            'forms_count': len(content.forms),
            'links_count': len(content.links),
            'text_length': len(content.text)
        }
        
        return metadata
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract structured data (JSON-LD, microdata, etc.)"""
        structured_data = {}
        
        # Extract JSON-LD
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    structured_data.update(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            structured_data.update(item)
            except json.JSONDecodeError:
                continue
        
        return structured_data
    
    def _extract_navigation(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract navigation menu items"""
        navigation = []
        
        # Find navigation elements
        nav_elements = soup.find_all(['nav', 'ul', 'ol'], class_=re.compile(r'nav|menu', re.I))
        
        for nav in nav_elements:
            links = nav.find_all('a', href=True)
            for link in links:
                text = link.get_text(strip=True)
                href = link.get('href')
                if text and href:
                    navigation.append({
                        'text': text,
                        'url': href
                    })
        
        return navigation
    
    def _extract_meta_tags(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta tags"""
        meta_tags = {}
        
        # Extract standard meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            if name and content:
                meta_tags[name] = content
        
        return meta_tags
    
    def _extract_forms(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract form information"""
        forms = []
        
        for form in soup.find_all('form'):
            form_data = {
                'action': form.get('action', ''),
                'method': form.get('method', 'GET'),
                'name': form.get('name', ''),
                'inputs': []
            }
            
            # Extract input fields
            for input_field in form.find_all(['input', 'select', 'textarea']):
                input_data = {
                    'type': input_field.get('type', input_field.name),
                    'name': input_field.get('name', ''),
                    'placeholder': input_field.get('placeholder', ''),
                    'required': input_field.has_attr('required')
                }
                form_data['inputs'].append(input_data)
            
            forms.append(form_data)
        
        return forms
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from the page"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href:
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                links.append(absolute_url)
        
        return links
    
    def _classify_service_type(self, service_data: Dict[str, Any]) -> ServiceType:
        """Classify service type based on service data"""
        service_text = str(service_data).lower()
        
        if any(keyword in service_text for keyword in ['book', 'reserve', 'appointment']):
            return ServiceType.BOOKING
        elif any(keyword in service_text for keyword in ['buy', 'purchase', 'cart', 'checkout']):
            return ServiceType.PURCHASE
        elif any(keyword in service_text for keyword in ['consult', 'advice', 'session']):
            return ServiceType.CONSULTATION
        elif any(keyword in service_text for keyword in ['subscribe', 'membership', 'plan']):
            return ServiceType.SUBSCRIPTION
        elif any(keyword in service_text for keyword in ['rent', 'lease', 'hire']):
            return ServiceType.RENTAL
        else:
            return ServiceType.BOOKING  # Default

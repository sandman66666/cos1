# File: chief_of_staff_ai/intelligence/web_scrapers.py
"""
Web Intelligence Scraping Workers
=================================
Automated LinkedIn, Twitter, and Company intelligence enrichment for contacts
"""

import asyncio
import logging
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import time
import random

# Web scraping
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class ContactEnrichment:
    """Enriched contact data from web intelligence"""
    email: str
    name: str = None
    company: str = None
    linkedin_data: Dict = None
    twitter_data: Dict = None
    company_data: Dict = None
    enrichment_status: str = 'completed'
    enrichment_timestamp: datetime = None
    confidence_score: float = 0.0

class RateLimiter:
    """Rate limiter for web scraping to avoid detection"""
    
    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self.min_delay = 60.0 / requests_per_minute
        self.last_request_time = 0
        
    async def wait(self):
        """Wait if necessary to respect rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            wait_time = self.min_delay - time_since_last
            # Add some randomness to avoid predictable patterns
            wait_time += random.uniform(0, 0.5)
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()

class BaseWebWorker:
    """Base class for web intelligence workers"""
    
    def __init__(self, rate_limit: int = 30):
        self.rate_limiter = RateLimiter(rate_limit)
        self.session = None
        self.playwright_browser = None
        self.playwright_context = None
        
    async def setup(self):
        """Initialize web scraping session"""
        try:
            # Setup httpx session
            self.session = httpx.AsyncClient(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                timeout=30.0
            )
            
            # Setup Playwright for JavaScript-heavy sites
            self.playwright = await async_playwright().start()
            self.playwright_browser = await self.playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self.playwright_context = await self.playwright_browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            logger.info(f"✅ {self.__class__.__name__} setup completed")
            
        except Exception as e:
            logger.error(f"❌ {self.__class__.__name__} setup failed: {str(e)}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.session:
                await self.session.aclose()
            if self.playwright_context:
                await self.playwright_context.close()
            if self.playwright_browser:
                await self.playwright_browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.warning(f"Cleanup warning: {str(e)}")
    
    async def safe_request(self, url: str, use_playwright: bool = False) -> Optional[str]:
        """Make a safe HTTP request with rate limiting"""
        await self.rate_limiter.wait()
        
        try:
            if use_playwright and self.playwright_context:
                page = await self.playwright_context.new_page()
                await page.goto(url, wait_until='networkidle')
                content = await page.content()
                await page.close()
                return content
            else:
                response = await self.session.get(url)
                response.raise_for_status()
                return response.text
                
        except Exception as e:
            logger.warning(f"Request failed for {url}: {str(e)}")
            return None

class LinkedInWorker(BaseWebWorker):
    """LinkedIn profile and activity intelligence worker"""
    
    def __init__(self):
        super().__init__(rate_limit=20)  # Conservative rate limiting for LinkedIn
        
    async def enrich_contact(self, name: str, company: str = None, email: str = None) -> Dict:
        """Enrich contact with LinkedIn intelligence"""
        try:
            logger.info(f"🔍 LinkedIn enrichment for {name} ({company or 'unknown company'})")
            
            # Search for LinkedIn profile
            profile_data = await self._search_linkedin_profile(name, company)
            
            if not profile_data:
                return {
                    'status': 'not_found',
                    'message': f'No LinkedIn profile found for {name}'
                }
            
            # Get detailed profile information
            detailed_data = await self._get_profile_details(profile_data.get('profile_url'))
            
            # Get recent activity
            activity_data = await self._get_recent_activity(profile_data.get('profile_url'))
            
            enrichment = {
                'status': 'success',
                'profile': profile_data,
                'details': detailed_data,
                'recent_activity': activity_data,
                'enrichment_timestamp': datetime.utcnow().isoformat(),
                'confidence': self._calculate_confidence(profile_data, name, company)
            }
            
            logger.info(f"✅ LinkedIn enrichment completed for {name} (confidence: {enrichment['confidence']:.2f})")
            return enrichment
            
        except Exception as e:
            logger.error(f"❌ LinkedIn enrichment failed for {name}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'enrichment_timestamp': datetime.utcnow().isoformat()
            }
    
    async def _search_linkedin_profile(self, name: str, company: str = None) -> Optional[Dict]:
        """Search for LinkedIn profile using Google search"""
        try:
            # Construct search query
            query_parts = [f'"{name}"', 'site:linkedin.com/in']
            if company:
                query_parts.append(f'"{company}"')
            
            search_query = ' '.join(query_parts)
            google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            content = await self.safe_request(google_url)
            if not content:
                return None
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find LinkedIn profile links
            linkedin_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'linkedin.com/in/' in href and '/url?q=' in href:
                    # Extract actual LinkedIn URL from Google redirect
                    linkedin_url = self._extract_linkedin_url(href)
                    if linkedin_url:
                        linkedin_links.append(linkedin_url)
            
            if not linkedin_links:
                return None
            
            # Return the first (most relevant) LinkedIn profile
            return {
                'profile_url': linkedin_links[0],
                'search_confidence': 0.8 if company else 0.6
            }
            
        except Exception as e:
            logger.warning(f"LinkedIn profile search failed: {str(e)}")
            return None
    
    def _extract_linkedin_url(self, google_url: str) -> Optional[str]:
        """Extract LinkedIn URL from Google search result redirect"""
        try:
            import urllib.parse
            if '/url?q=' in google_url:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(google_url).query)
                if 'q' in parsed:
                    url = parsed['q'][0]
                    if 'linkedin.com/in/' in url:
                        return url.split('&')[0]  # Remove additional parameters
            return None
        except:
            return None
    
    async def _get_profile_details(self, profile_url: str) -> Dict:
        """Get detailed LinkedIn profile information"""
        try:
            # Note: This is a simplified version. In production, you'd use LinkedIn API
            # or more sophisticated scraping techniques
            
            content = await self.safe_request(profile_url, use_playwright=True)
            if not content:
                return {}
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract basic information (this is simplified - real implementation would be more robust)
            profile_data = {
                'headline': self._extract_text(soup, 'h1'),
                'current_position': self._extract_text(soup, '.pv-text-details__left-panel h2'),
                'location': self._extract_text(soup, '.pv-text-details__left-panel .pb2'),
                'connection_count': self._extract_connection_count(soup),
                'profile_completeness': 0.7,  # Estimated
            }
            
            return profile_data
            
        except Exception as e:
            logger.warning(f"LinkedIn profile details extraction failed: {str(e)}")
            return {}
    
    async def _get_recent_activity(self, profile_url: str) -> List[Dict]:
        """Get recent LinkedIn activity and posts"""
        try:
            # In a real implementation, this would scrape recent posts and activity
            # For now, return placeholder data
            return [
                {
                    'type': 'post',
                    'content': 'Recent activity placeholder',
                    'date': (datetime.utcnow() - timedelta(days=2)).isoformat(),
                    'engagement': {'likes': 10, 'comments': 2}
                }
            ]
            
        except Exception as e:
            logger.warning(f"LinkedIn activity extraction failed: {str(e)}")
            return []
    
    def _extract_text(self, soup: BeautifulSoup, selector: str) -> str:
        """Safely extract text from BeautifulSoup element"""
        try:
            element = soup.select_one(selector)
            return element.get_text(strip=True) if element else ""
        except:
            return ""
    
    def _extract_connection_count(self, soup: BeautifulSoup) -> int:
        """Extract LinkedIn connection count"""
        try:
            # Look for connection count patterns
            connection_text = self._extract_text(soup, '.pv-top-card--list-bullet li')
            if 'connection' in connection_text.lower():
                numbers = re.findall(r'(\d+)', connection_text)
                if numbers:
                    return int(numbers[0])
            return 0
        except:
            return 0
    
    def _calculate_confidence(self, profile_data: Dict, name: str, company: str) -> float:
        """Calculate confidence score for LinkedIn match"""
        confidence = profile_data.get('search_confidence', 0.5)
        
        # Boost confidence if company matches
        if company and profile_data.get('current_position'):
            if company.lower() in profile_data['current_position'].lower():
                confidence += 0.2
        
        return min(confidence, 1.0)

class TwitterWorker(BaseWebWorker):
    """Twitter profile and activity intelligence worker"""
    
    def __init__(self):
        super().__init__(rate_limit=25)  # Conservative rate limiting for Twitter
        
    async def enrich_contact(self, name: str, company: str = None, email: str = None) -> Dict:
        """Enrich contact with Twitter intelligence"""
        try:
            logger.info(f"🐦 Twitter enrichment for {name} ({company or 'unknown company'})")
            
            # Search for Twitter profile
            profile_data = await self._search_twitter_profile(name, company)
            
            if not profile_data:
                return {
                    'status': 'not_found',
                    'message': f'No Twitter profile found for {name}'
                }
            
            # Get recent tweets
            tweets_data = await self._get_recent_tweets(profile_data.get('handle'))
            
            enrichment = {
                'status': 'success',
                'profile': profile_data,
                'recent_tweets': tweets_data,
                'enrichment_timestamp': datetime.utcnow().isoformat(),
                'confidence': self._calculate_confidence(profile_data, name, company)
            }
            
            logger.info(f"✅ Twitter enrichment completed for {name} (confidence: {enrichment['confidence']:.2f})")
            return enrichment
            
        except Exception as e:
            logger.error(f"❌ Twitter enrichment failed for {name}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'enrichment_timestamp': datetime.utcnow().isoformat()
            }
    
    async def _search_twitter_profile(self, name: str, company: str = None) -> Optional[Dict]:
        """Search for Twitter profile"""
        try:
            # Search using Google for Twitter profiles
            query_parts = [f'"{name}"', 'site:twitter.com']
            if company:
                query_parts.append(f'"{company}"')
            
            search_query = ' '.join(query_parts)
            google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
            
            content = await self.safe_request(google_url)
            if not content:
                return None
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find Twitter profile links
            twitter_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'twitter.com/' in href and '/url?q=' in href:
                    twitter_url = self._extract_twitter_url(href)
                    if twitter_url:
                        twitter_links.append(twitter_url)
            
            if not twitter_links:
                return None
            
            # Extract handle from URL
            handle = self._extract_handle_from_url(twitter_links[0])
            
            return {
                'profile_url': twitter_links[0],
                'handle': handle,
                'search_confidence': 0.7 if company else 0.5
            }
            
        except Exception as e:
            logger.warning(f"Twitter profile search failed: {str(e)}")
            return None
    
    def _extract_twitter_url(self, google_url: str) -> Optional[str]:
        """Extract Twitter URL from Google search result"""
        try:
            import urllib.parse
            if '/url?q=' in google_url:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(google_url).query)
                if 'q' in parsed:
                    url = parsed['q'][0]
                    if 'twitter.com/' in url:
                        return url.split('&')[0]
            return None
        except:
            return None
    
    def _extract_handle_from_url(self, twitter_url: str) -> str:
        """Extract Twitter handle from URL"""
        try:
            parts = twitter_url.split('/')
            for i, part in enumerate(parts):
                if part == 'twitter.com' and i + 1 < len(parts):
                    return parts[i + 1].split('?')[0]  # Remove query parameters
            return ""
        except:
            return ""
    
    async def _get_recent_tweets(self, handle: str) -> List[Dict]:
        """Get recent tweets from handle"""
        try:
            if not handle:
                return []
            
            # In a real implementation, you'd use Twitter API or scraping
            # For now, return placeholder data
            return [
                {
                    'content': f'Recent tweet placeholder from @{handle}',
                    'date': (datetime.utcnow() - timedelta(days=1)).isoformat(),
                    'engagement': {'likes': 5, 'retweets': 2, 'replies': 1}
                }
            ]
            
        except Exception as e:
            logger.warning(f"Twitter tweets extraction failed: {str(e)}")
            return []
    
    def _calculate_confidence(self, profile_data: Dict, name: str, company: str) -> float:
        """Calculate confidence score for Twitter match"""
        return profile_data.get('search_confidence', 0.5)

class CompanyIntelWorker(BaseWebWorker):
    """Company intelligence and background research worker"""
    
    def __init__(self):
        super().__init__(rate_limit=40)  # More permissive for general web scraping
        
    async def enrich_company(self, company_name: str, domain: str = None) -> Dict:
        """Enrich company information"""
        try:
            logger.info(f"🏢 Company enrichment for {company_name}")
            
            # Get company website data
            website_data = await self._get_website_data(company_name, domain)
            
            # Get company news and mentions
            news_data = await self._get_company_news(company_name)
            
            # Get funding and investment information
            funding_data = await self._get_funding_info(company_name)
            
            enrichment = {
                'status': 'success',
                'company_name': company_name,
                'website_data': website_data,
                'news_mentions': news_data,
                'funding_info': funding_data,
                'enrichment_timestamp': datetime.utcnow().isoformat(),
                'confidence': self._calculate_company_confidence(website_data, news_data)
            }
            
            logger.info(f"✅ Company enrichment completed for {company_name}")
            return enrichment
            
        except Exception as e:
            logger.error(f"❌ Company enrichment failed for {company_name}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'enrichment_timestamp': datetime.utcnow().isoformat()
            }
    
    async def _get_website_data(self, company_name: str, domain: str = None) -> Dict:
        """Get company website information"""
        try:
            if domain:
                website_url = f"https://{domain}"
            else:
                # Search for company website
                search_query = f'"{company_name}" official website'
                google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
                
                content = await self.safe_request(google_url)
                if not content:
                    return {}
                
                soup = BeautifulSoup(content, 'html.parser')
                website_url = self._extract_company_website(soup, company_name)
                
                if not website_url:
                    return {}
            
            # Get website content
            website_content = await self.safe_request(website_url)
            if not website_content:
                return {}
            
            soup = BeautifulSoup(website_content, 'html.parser')
            
            return {
                'url': website_url,
                'title': soup.title.string if soup.title else "",
                'description': self._extract_meta_description(soup),
                'industry_keywords': self._extract_industry_keywords(soup),
                'employee_count_estimate': self._estimate_company_size(soup),
                'technologies': self._detect_technologies(website_content)
            }
            
        except Exception as e:
            logger.warning(f"Website data extraction failed: {str(e)}")
            return {}
    
    def _extract_company_website(self, soup: BeautifulSoup, company_name: str) -> Optional[str]:
        """Extract company website from Google search results"""
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/url?q=' in href:
                try:
                    import urllib.parse
                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                    if 'q' in parsed:
                        url = parsed['q'][0]
                        # Basic heuristics to identify company website
                        if (not any(domain in url for domain in ['linkedin.com', 'twitter.com', 'facebook.com', 'crunchbase.com']) and
                            ('http' in url) and 
                            (company_name.lower().replace(' ', '') in url.lower() or
                             any(word in url.lower() for word in company_name.lower().split()))):
                            return url.split('&')[0]
                except:
                    continue
        return None
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description from website"""
        try:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                return meta_desc.get('content', '')
        except:
            pass
        return ""
    
    def _extract_industry_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract industry-related keywords from website"""
        try:
            text_content = soup.get_text().lower()
            
            # Common industry keywords
            industry_keywords = [
                'software', 'technology', 'fintech', 'healthcare', 'biotech',
                'manufacturing', 'retail', 'consulting', 'marketing', 'advertising',
                'real estate', 'construction', 'education', 'nonprofit', 'media',
                'entertainment', 'gaming', 'automotive', 'aerospace', 'energy'
            ]
            
            found_keywords = []
            for keyword in industry_keywords:
                if keyword in text_content:
                    found_keywords.append(keyword)
            
            return found_keywords[:5]  # Return top 5 matches
            
        except:
            return []
    
    def _estimate_company_size(self, soup: BeautifulSoup) -> str:
        """Estimate company size from website content"""
        try:
            text_content = soup.get_text().lower()
            
            # Look for size indicators
            if any(term in text_content for term in ['enterprise', 'fortune 500', 'global', 'worldwide']):
                return 'large'
            elif any(term in text_content for term in ['startup', 'small team', 'growing']):
                return 'small'
            else:
                return 'medium'
                
        except:
            return 'unknown'
    
    def _detect_technologies(self, html_content: str) -> List[str]:
        """Detect technologies used on the website"""
        try:
            technologies = []
            
            # Simple technology detection
            tech_patterns = {
                'react': r'react',
                'angular': r'angular',
                'vue': r'vue\.js',
                'wordpress': r'wp-content',
                'shopify': r'shopify',
                'google_analytics': r'google-analytics|gtag',
                'jquery': r'jquery'
            }
            
            for tech, pattern in tech_patterns.items():
                if re.search(pattern, html_content.lower()):
                    technologies.append(tech)
            
            return technologies
            
        except:
            return []
    
    async def _get_company_news(self, company_name: str) -> List[Dict]:
        """Get recent company news and mentions"""
        try:
            # Search for recent news
            search_query = f'"{company_name}" news'
            google_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&tbm=nws"
            
            content = await self.safe_request(google_url)
            if not content:
                return []
            
            # Parse news results (simplified)
            return [
                {
                    'title': f'Recent news about {company_name}',
                    'source': 'News Source',
                    'date': (datetime.utcnow() - timedelta(days=3)).isoformat(),
                    'snippet': 'News snippet placeholder'
                }
            ]
            
        except Exception as e:
            logger.warning(f"Company news extraction failed: {str(e)}")
            return []
    
    async def _get_funding_info(self, company_name: str) -> Dict:
        """Get company funding and investment information"""
        try:
            # In a real implementation, you'd query Crunchbase API or similar
            return {
                'funding_stage': 'unknown',
                'total_funding': 'unknown',
                'last_funding_date': None,
                'investors': []
            }
            
        except Exception as e:
            logger.warning(f"Funding info extraction failed: {str(e)}")
            return {}
    
    def _calculate_company_confidence(self, website_data: Dict, news_data: List[Dict]) -> float:
        """Calculate confidence score for company enrichment"""
        confidence = 0.3  # Base confidence
        
        if website_data.get('url'):
            confidence += 0.4
        if website_data.get('description'):
            confidence += 0.2
        if news_data:
            confidence += 0.1
        
        return min(confidence, 1.0)

class WebIntelligenceManager:
    """Manages and coordinates all web intelligence workers"""
    
    def __init__(self):
        self.linkedin_worker = LinkedInWorker()
        self.twitter_worker = TwitterWorker()
        self.company_worker = CompanyIntelWorker()
        self.initialized = False
    
    async def initialize(self):
        """Initialize all web workers"""
        if self.initialized:
            return
            
        try:
            logger.info("🔧 Initializing Web Intelligence Manager...")
            
            # Initialize all workers in parallel
            await asyncio.gather(
                self.linkedin_worker.setup(),
                self.twitter_worker.setup(),
                self.company_worker.setup()
            )
            
            self.initialized = True
            logger.info("✅ Web Intelligence Manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Web Intelligence Manager initialization failed: {str(e)}")
            raise
    
    async def enrich_contact_batch(self, contacts: List[Dict]) -> List[ContactEnrichment]:
        """Enrich a batch of contacts with web intelligence"""
        if not self.initialized:
            await self.initialize()
        
        enriched_contacts = []
        
        for i, contact in enumerate(contacts):
            try:
                logger.info(f"🔍 Enriching contact {i+1}/{len(contacts)}: {contact.get('email', 'unknown')}")
                
                # Run LinkedIn and Twitter enrichment in parallel
                linkedin_task = self.linkedin_worker.enrich_contact(
                    contact.get('name', ''),
                    contact.get('company', ''),
                    contact.get('email', '')
                )
                
                twitter_task = self.twitter_worker.enrich_contact(
                    contact.get('name', ''),
                    contact.get('company', ''),
                    contact.get('email', '')
                )
                
                linkedin_data, twitter_data = await asyncio.gather(
                    linkedin_task, twitter_task, return_exceptions=True
                )
                
                # Handle exceptions
                if isinstance(linkedin_data, Exception):
                    logger.warning(f"LinkedIn enrichment failed: {str(linkedin_data)}")
                    linkedin_data = {'status': 'error', 'error': str(linkedin_data)}
                
                if isinstance(twitter_data, Exception):
                    logger.warning(f"Twitter enrichment failed: {str(twitter_data)}")
                    twitter_data = {'status': 'error', 'error': str(twitter_data)}
                
                # Enrich company data if available
                company_data = {}
                if contact.get('company'):
                    try:
                        company_data = await self.company_worker.enrich_company(contact['company'])
                    except Exception as e:
                        logger.warning(f"Company enrichment failed: {str(e)}")
                        company_data = {'status': 'error', 'error': str(e)}
                
                # Calculate overall confidence
                confidence = self._calculate_overall_confidence(linkedin_data, twitter_data, company_data)
                
                enriched_contact = ContactEnrichment(
                    email=contact.get('email', ''),
                    name=contact.get('name', ''),
                    company=contact.get('company', ''),
                    linkedin_data=linkedin_data,
                    twitter_data=twitter_data,
                    company_data=company_data,
                    enrichment_status='completed',
                    enrichment_timestamp=datetime.utcnow(),
                    confidence_score=confidence
                )
                
                enriched_contacts.append(enriched_contact)
                
                logger.info(f"✅ Contact enriched: {contact.get('email', 'unknown')} (confidence: {confidence:.2f})")
                
                # Small delay to be respectful to servers
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Contact enrichment failed for {contact.get('email', 'unknown')}: {str(e)}")
                
                # Add failed enrichment
                enriched_contacts.append(ContactEnrichment(
                    email=contact.get('email', ''),
                    name=contact.get('name', ''),
                    company=contact.get('company', ''),
                    enrichment_status='failed',
                    enrichment_timestamp=datetime.utcnow(),
                    confidence_score=0.0
                ))
        
        logger.info(f"🎯 Batch enrichment completed: {len(enriched_contacts)} contacts processed")
        return enriched_contacts
    
    def _calculate_overall_confidence(self, linkedin_data: Dict, twitter_data: Dict, company_data: Dict) -> float:
        """Calculate overall confidence score for contact enrichment"""
        confidences = []
        
        if linkedin_data.get('status') == 'success':
            confidences.append(linkedin_data.get('confidence', 0.0))
        
        if twitter_data.get('status') == 'success':
            confidences.append(twitter_data.get('confidence', 0.0))
        
        if company_data.get('status') == 'success':
            confidences.append(company_data.get('confidence', 0.0))
        
        if not confidences:
            return 0.0
        
        # Weight LinkedIn more heavily as it's typically more reliable for professional contacts
        if len(confidences) >= 2 and linkedin_data.get('status') == 'success':
            linkedin_confidence = linkedin_data.get('confidence', 0.0)
            other_confidences = [c for c in confidences if c != linkedin_confidence]
            return (linkedin_confidence * 0.6) + (sum(other_confidences) / len(other_confidences) * 0.4)
        
        return sum(confidences) / len(confidences)
    
    async def cleanup(self):
        """Clean up all web workers"""
        if not self.initialized:
            return
            
        try:
            await asyncio.gather(
                self.linkedin_worker.cleanup(),
                self.twitter_worker.cleanup(),
                self.company_worker.cleanup()
            )
            logger.info("✅ Web Intelligence Manager cleanup completed")
        except Exception as e:
            logger.warning(f"Cleanup warning: {str(e)}") 
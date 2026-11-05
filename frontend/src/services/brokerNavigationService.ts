import { CompanyTradingRoute, BrokerDestination } from '../types';
import { api } from './api';
import { getClientSideTradingRoute } from '../utils/tickerLookup';
import { BrokerId, getSelectedBroker } from '../utils/brokerConfig';

export interface BrokerNavigationQuery {
  company?: string;
  ticker?: string;
  exchange?: string;
  country?: string;
  preferredBrokerId?: BrokerId;
  brokerInstrumentKey?: string;
}

export interface NavigationResult {
  success: boolean;
  openedUrl?: string;
  destinationType: 'direct_instrument' | 'verified_portal_with_ticker_search' | 'unsupported';
  isBlockedByPopup?: boolean;
  message?: string;
}

class BrokerNavigationService {
  /**
   * Resolves a fully verified trading route for a stock or news headline.
   * Leverages immediate deterministic client-side verification as instant baseline
   * and queries the backend API for live backend instrument metadata.
   */
  async resolveRoute(query: BrokerNavigationQuery): Promise<CompanyTradingRoute> {
    const { company, ticker, preferredBrokerId } = query;
    const broker = preferredBrokerId || getSelectedBroker();

    // 1. Instant deterministic client resolution matching requested broker
    const clientRoute = getClientSideTradingRoute(company, ticker, broker);

    try {
      // 2. Fetch backend confirmed route with preferred broker
      const backendRoute = await api.getTradingRoute(company, ticker, broker);
      if (backendRoute && backendRoute.status === 'supported') {
        return backendRoute;
      }
      return clientRoute;
    } catch (err) {
      console.debug('Using verified client fallback trading route:', err);
      return clientRoute;
    }
  }

  /**
   * Returns the primary URL to navigate to for a given route and broker destination.
   * If a verified direct instrument URL is available and preferred, returns that.
   * Strictly respects the broker identity (Upstox vs Groww) to prevent wrong redirections.
   */
  getDestinationUrl(
    route: CompanyTradingRoute,
    broker: BrokerDestination,
    destinationPreference: 'direct' | 'portal' = 'direct'
  ): string {
    if (!route.is_tradable) {
      return '';
    }

    const brokerId = broker.broker_id?.toLowerCase();

    // Find the specific broker destination in the route's broker list if possible
    const matchingBroker = route.brokers.find(
      (b) => b.broker_id.toLowerCase() === brokerId
    ) || broker;

    if (destinationPreference === 'direct' && matchingBroker.direct_url) {
      return matchingBroker.direct_url;
    }

    if (destinationPreference === 'portal') {
      if (brokerId === 'upstox') {
        return 'https://pro.upstox.com';
      }
      if (brokerId === 'groww') {
        return 'https://groww.in/stocks';
      }
      if (route.portal_fallback_url) {
        return route.portal_fallback_url;
      }
    }

    return (
      matchingBroker.direct_url ||
      matchingBroker.entry_url ||
      (brokerId === 'upstox' ? 'https://pro.upstox.com' : 'https://groww.in/stocks')
    );
  }

  /**
   * Safely opens a broker destination in a new browser tab with security flags.
   * Defends against popup blockers and validates HTTPS protocol.
   */
  openDestination(
    route: CompanyTradingRoute,
    broker: BrokerDestination,
    destinationPreference: 'direct' | 'portal' = 'direct'
  ): NavigationResult {
    const targetUrl = this.getDestinationUrl(route, broker, destinationPreference);

    if (!targetUrl) {
      return {
        success: false,
        destinationType: 'unsupported',
        message: 'No verified broker destination URL available for this security.'
      };
    }

    // Safety verification: URL must use secure HTTPS protocol
    try {
      const parsed = new URL(targetUrl);
      if (parsed.protocol !== 'https:') {
        return {
          success: false,
          destinationType: route.destination_type || 'unsupported',
          message: 'Destination URL failed security validation (HTTPS required).'
        };
      }
    } catch {
      return {
        success: false,
        destinationType: route.destination_type || 'unsupported',
        message: 'Invalid destination URL format.'
      };
    }

    try {
      const openedWindow = window.open(targetUrl, '_blank', 'noopener,noreferrer');
      if (!openedWindow || openedWindow.closed || typeof openedWindow.closed === 'undefined') {
        return {
          success: false,
          openedUrl: targetUrl,
          destinationType: route.destination_type || 'unsupported',
          isBlockedByPopup: true,
          message: 'Pop-up window was blocked by your browser. Please allow popups or use the direct link.'
        };
      }

      return {
        success: true,
        openedUrl: targetUrl,
        destinationType: route.destination_type || 'unsupported',
        message: `Successfully navigated to ${broker.broker_name}.`
      };
    } catch (e: any) {
      return {
        success: false,
        openedUrl: targetUrl,
        destinationType: route.destination_type || 'unsupported',
        message: e?.message || 'Failed to open broker destination.'
      };
    }
  }

  /**
   * Generates a clear, contextual primary action label.
   */
  getActionLabel(route: CompanyTradingRoute, broker: BrokerDestination): string {
    if (route.action_label) {
      return route.action_label;
    }
    if (broker.action_label) {
      return broker.action_label;
    }
    const shortName = route.company.split(' ')[0] || route.ticker || 'Stock';
    return `Open ${shortName} in ${broker.broker_name}`;
  }
}

export const brokerNavigationService = new BrokerNavigationService();


import { useEffect } from 'react';
import { useSearchStore } from '../store/searchStore';
import { RetrievalStage } from '../types/search';

export function useSearchWebsocket() {
  const { updatePipelineStage } = useSearchStore();

  useEffect(() => {
    // Use direct connection to backend to avoid any Vite proxy/HMR conflicts
    const wsUrl = `ws://localhost:8000/ws/pipeline`;
    
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Search WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'domain_event') {
          const data = payload.event;
          
          switch (data.event_type) {
            case 'search.started':
              // Reset is handled by the startSearch action, but we can ensure it here
              break;
              
            case 'retrieval.stage_completed':
              if (data.stage) {
                updatePipelineStage(
                  data.stage as RetrievalStage, 
                  data.status === 'failed' ? 'failed' : 'completed',
                  data.latency_ms
                );
              }
              break;

            case 'retrieval.fusion_completed':
              updatePipelineStage(RetrievalStage.RESULT_FUSION, 'completed', data.latency_ms);
              break;

            case 'retrieval.results_ranked':
              updatePipelineStage(RetrievalStage.RERANKING, 'completed', data.latency_ms);
              break;

            case 'search.completed':
            case 'search.failed':
              // Finalization is handled by the REST API response settling, but we could update UI here too
              break;
          }
        }
      } catch (err) {
        console.error('Error parsing WS message', err);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket Error', error);
    };

    ws.onclose = () => {
      console.log('Search WebSocket disconnected');
    };

    return () => {
      ws.close();
    };
  }, []); // Run once on mount
}

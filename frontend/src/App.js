import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import {
  AppBar,
  Toolbar,
  Typography,
  Chip,
  Box,
  ThemeProvider,
  createTheme,
  CssBaseline,
  IconButton,
  Tooltip,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import StorageIcon from '@mui/icons-material/Storage';
import ArticleIcon from '@mui/icons-material/Article';
import SessionList from './components/SessionList';
import ChatPane from './components/ChatPane';
import ArtifactViewer from './components/ArtifactViewer';
import './App.css';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563eb',
      light: '#60a5fa',
      dark: '#1d4ed8',
    },
    secondary: {
      main: '#7c3aed',
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
  shape: {
    borderRadius: 8,
  },
});

function App() {
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [providerConfig, setProviderConfig] = useState(null);
  const [artifactRefreshTrigger, setArtifactRefreshTrigger] = useState(0);
  const [showArtifactViewer, setShowArtifactViewer] = useState(false);
  const [hasArtifacts, setHasArtifacts] = useState(false);
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const fetchSessions = useCallback(async () => {
    try {
      const response = await axios.get(`${apiUrl}/sessions`);
      setSessions(response.data || []);

      if (response.data && response.data.length > 0 && !currentSessionId) {
        setCurrentSessionId(response.data[0].id);
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  }, [apiUrl, currentSessionId]);

  const fetchConfig = useCallback(async () => {
    try {
      const response = await axios.get(`${apiUrl}/config`);
      setProviderConfig(response.data);
    } catch (error) {
      console.error('Error fetching config:', error);
      setProviderConfig({ available: false, display_name: 'Ollama Offline' });
    }
  }, [apiUrl]);

  // Check if current session has artifacts
  const checkArtifacts = useCallback(async (sessionId) => {
    if (!sessionId) {
      setHasArtifacts(false);
      setShowArtifactViewer(false);
      return;
    }
    try {
      const response = await axios.get(`${apiUrl}/sessions/${sessionId}/artifacts`);
      const list = response.data || [];
      const hasAny = list.length > 0;
      setHasArtifacts(hasAny);
    } catch (error) {
      setHasArtifacts(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchSessions();
    fetchConfig();
    const interval = setInterval(fetchSessions, 10000);
    return () => clearInterval(interval);
  }, [fetchSessions, fetchConfig]);

  useEffect(() => {
    checkArtifacts(currentSessionId);
  }, [currentSessionId, artifactRefreshTrigger, checkArtifacts]);

  const handleSessionSelect = (sessionId) => {
    setCurrentSessionId(sessionId);
    checkArtifacts(sessionId);
  };

  const handleNewSession = async () => {
    try {
      const response = await axios.post(`${apiUrl}/sessions`, {
        title: 'New Chat',
      });
      const newSession = response.data;
      setSessions((prev) => [newSession, ...prev]);
      setCurrentSessionId(newSession.id);
      setShowArtifactViewer(false);
      setHasArtifacts(false);
    } catch (error) {
      console.error('Error creating new session:', error);
    }
  };

  // Called when an artifact (like Ship 30 essay) is generated
  const triggerArtifactRefresh = () => {
    setArtifactRefreshTrigger((prev) => prev + 1);
    setShowArtifactViewer(true);
    setHasArtifacts(true);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh', bgcolor: 'background.default' }}>
        {/* Header */}
        <AppBar position="static" elevation={0} sx={{ borderBottom: '1px solid #e2e8f0', bgcolor: '#ffffff', color: '#1e293b' }}>
          <Toolbar variant="dense" sx={{ display: 'flex', justifyContent: 'space-between', py: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <AutoAwesomeIcon sx={{ color: 'primary.main', fontSize: 24 }} />
              <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: '-0.025em', color: '#0f172a' }}>
                Lenny Growth Assistant
              </Typography>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {/* Artifact toggle button (like Claude) */}
              {hasArtifacts && (
                <Tooltip title={showArtifactViewer ? 'Hide Artifacts Pane' : 'Show Artifacts Pane'}>
                  <Chip
                    icon={<ArticleIcon sx={{ fontSize: '15px !important' }} />}
                    label={showArtifactViewer ? 'Artifacts Open' : 'View Artifacts'}
                    size="small"
                    color={showArtifactViewer ? 'secondary' : 'default'}
                    variant={showArtifactViewer ? 'filled' : 'outlined'}
                    onClick={() => setShowArtifactViewer((prev) => !prev)}
                    clickable
                    sx={{ fontWeight: 600, fontSize: '0.75rem' }}
                  />
                </Tooltip>
              )}

              <Chip
                icon={<StorageIcon sx={{ fontSize: '14px !important' }} />}
                label="Supabase Vector DB"
                size="small"
                color="success"
                variant="outlined"
                sx={{ fontWeight: 500, fontSize: '0.75rem' }}
              />
              <Chip
                label={providerConfig ? `${providerConfig.available ? '🟢' : '🔴'} ${providerConfig.display_name}` : 'Checking LLM...'}
                size="small"
                variant="outlined"
                color={providerConfig?.available ? 'primary' : 'default'}
                sx={{ fontWeight: 500, fontSize: '0.75rem' }}
              />
            </Box>
          </Toolbar>
        </AppBar>

        {/* Body Layout: Left Sidebar + Center Chat + Optional Right Artifact Viewer */}
        <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
          {/* Left: Session List */}
          <Box
            sx={{
              width: 280,
              minWidth: 240,
              borderRight: '1px solid #e2e8f0',
              bgcolor: '#ffffff',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <SessionList
              sessions={sessions}
              currentSessionId={currentSessionId}
              onSessionSelect={handleSessionSelect}
              onNewSession={handleNewSession}
            />
          </Box>

          {/* Center: Chat Pane (Expands when Artifact Viewer is closed) */}
          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', bgcolor: '#ffffff' }}>
            <ChatPane
              sessionId={currentSessionId}
              onSessionChange={setCurrentSessionId}
              onArtifactCreated={triggerArtifactRefresh}
            />
          </Box>

          {/* Right: Artifact Viewer (Claude-style dynamic drawer / pane) */}
          {showArtifactViewer && (
            <Box
              sx={{
                width: 460,
                minWidth: 380,
                maxWidth: '45vw',
                borderLeft: '1px solid #e2e8f0',
                bgcolor: '#ffffff',
                display: 'flex',
                flexDirection: 'column',
                animation: 'fadeIn 0.2s ease-in-out',
              }}
            >
              <ArtifactViewer
                sessionId={currentSessionId}
                refreshTrigger={artifactRefreshTrigger}
                onClose={() => setShowArtifactViewer(false)}
              />
            </Box>
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;
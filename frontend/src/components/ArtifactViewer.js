import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Box,
  Typography,
  CircularProgress,
  Tab,
  Tabs,
  Paper,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import ReactMarkdown from 'react-markdown';

import CloseIcon from '@mui/icons-material/Close';

const ArtifactViewer = ({ sessionId, refreshTrigger, onClose }) => {
  const [artifacts, setArtifacts] = useState([]);
  const [selectedTab, setSelectedTab] = useState(0);
  const [loading, setLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [error, setError] = useState(null);

  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    if (!sessionId) {
      setArtifacts([]);
      setLoading(false);
      setError(null);
      return;
    }

    const fetchArtifacts = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`${apiUrl}/sessions/${sessionId}/artifacts`);
        setArtifacts(response.data || []);
      } catch (err) {
        console.error('Error fetching artifacts:', err);
        setError('Failed to load artifacts.');
        setArtifacts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchArtifacts();
  }, [sessionId, apiUrl, refreshTrigger]);

  const handleCopy = (id, content) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!sessionId) {
    return (
      <Box
        sx={{
          p: 3,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'text.secondary',
        }}
      >
        <AutoAwesomeIcon sx={{ fontSize: 40, mb: 1, color: 'text.disabled' }} />
        <Typography variant="body2">Select a session to view artifacts</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', bgcolor: 'background.paper' }}>
      {/* Header */}
      <Box
        sx={{
          px: 2.5,
          py: 1.5,
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Artifacts & Essays
          </Typography>
          <Chip
            label={`${artifacts.length} ${artifacts.length === 1 ? 'item' : 'items'}`}
            size="small"
            variant="outlined"
            sx={{ fontSize: '0.75rem' }}
          />
        </Box>
        {onClose && (
          <Tooltip title="Close Artifact Viewer">
            <IconButton size="small" onClick={onClose}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: '1px solid', borderColor: 'divider', px: 2 }}>
        <Tabs value={selectedTab} onChange={(e, v) => setSelectedTab(v)} size="small">
          <Tab label="Rendered View" sx={{ textTransform: 'none', fontWeight: 500 }} />
          <Tab label="Raw Markdown" sx={{ textTransform: 'none', fontWeight: 500 }} />
        </Tabs>
      </Box>

      {/* Content Area */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 2.5 }}>
        {loading && artifacts.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <CircularProgress size={24} />
            <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
              Loading artifacts...
            </Typography>
          </Box>
        )}

        {!loading && artifacts.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 8, color: 'text.secondary' }}>
            <Typography variant="body2">No artifacts generated in this session yet.</Typography>
            <Typography variant="caption" sx={{ display: 'block', mt: 1 }}>
              Generate an essay in <b>Ship 30 mode</b> to see structured deliverables here.
            </Typography>
          </Box>
        )}

        {artifacts.map((artifact) => {
          const type = (artifact.artifact_type || artifact.kind || 'markdown').toLowerCase();
          const isHtml = type === 'html';
          const isShip30 = type === 'ship30';

          return (
            <Paper
              key={artifact.id}
              elevation={0}
              sx={{
                mb: 3,
                p: 2.5,
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider',
                bgcolor: '#fafafa',
              }}
            >
              {/* Artifact metadata bar */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mb: 2,
                  pb: 1.5,
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Chip
                    label={isShip30 ? 'Ship 30 Essay' : isHtml ? 'HTML Artifact' : 'Markdown'}
                    size="small"
                    color={isShip30 ? 'secondary' : 'primary'}
                    sx={{ height: 22, fontSize: '0.72rem', fontWeight: 600 }}
                  />
                  {artifact.word_count > 0 && (
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      {artifact.word_count} words
                    </Typography>
                  )}
                </Box>

                <Tooltip title="Copy Content">
                  <IconButton size="small" onClick={() => handleCopy(artifact.id, artifact.content || '')}>
                    {copiedId === artifact.id ? (
                      <CheckIcon fontSize="small" color="success" />
                    ) : (
                      <ContentCopyIcon fontSize="small" />
                    )}
                  </IconButton>
                </Tooltip>
              </Box>

              {/* Rendered Tab */}
              {selectedTab === 0 && (
                <Box>
                  {isHtml ? (
                    <iframe
                      title={`Artifact ${artifact.id}`}
                      srcDoc={artifact.content || ''}
                      sandbox="allow-same-origin"
                      style={{
                        width: '100%',
                        minHeight: '350px',
                        border: '1px solid #e2e8f0',
                        borderRadius: '6px',
                        backgroundColor: '#ffffff',
                      }}
                    />
                  ) : (
                    <Box
                      sx={{
                        fontSize: '0.92rem',
                        lineHeight: 1.6,
                        color: '#1e293b',
                        '& h1, & h2, & h3': { color: '#0f172a', mt: 2, mb: 1, fontWeight: 700 },
                        '& h2': { fontSize: '1.25rem', borderBottom: '1px solid #e2e8f0', pb: 0.5 },
                        '& p': { mb: 1.5 },
                        '& ul, & ol': { pl: 3, mb: 1.5 },
                        '& strong': { color: '#0f172a', fontWeight: 600 },
                        '& blockquote': {
                          borderLeft: '4px solid #2563eb',
                          pl: 2,
                          py: 0.5,
                          my: 1.5,
                          color: '#475569',
                          fontStyle: 'italic',
                        },
                      }}
                    >
                      <ReactMarkdown>{artifact.content || ''}</ReactMarkdown>
                    </Box>
                  )}
                </Box>
              )}

              {/* Source Tab */}
              {selectedTab === 1 && (
                <Box
                  component="pre"
                  sx={{
                    p: 2,
                    m: 0,
                    bgcolor: '#0f172a',
                    color: '#f8fafc',
                    borderRadius: 1.5,
                    fontSize: '0.82rem',
                    fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    lineHeight: 1.5,
                  }}
                >
                  {artifact.content || ''}
                </Box>
              )}
            </Paper>
          );
        })}
      </Box>
    </Box>
  );
};

export default ArtifactViewer;
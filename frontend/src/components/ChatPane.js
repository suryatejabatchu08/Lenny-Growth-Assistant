import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Box,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Chip,
  Paper,
  IconButton,
  Tooltip,
  ButtonGroup,
} from '@mui/material';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SendIcon from '@mui/icons-material/Send';
import ArticleIcon from '@mui/icons-material/Article';
import HistoryEduIcon from '@mui/icons-material/HistoryEdu';
import CloseIcon from '@mui/icons-material/Close';
import ReactMarkdown from 'react-markdown';

const ChatPane = ({ sessionId, onSessionChange, onArtifactCreated }) => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('qa'); // 'qa' | 'ship30'
  const messagesEndRef = useRef(null);
  const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Fetch messages for current session
  useEffect(() => {
    if (!sessionId) {
      setMessages([]);
      return;
    }

    const fetchMessages = async () => {
      try {
        const response = await axios.get(`${apiUrl}/sessions/${sessionId}/messages`);
        setMessages(response.data || []);
      } catch (error) {
        console.error('Error fetching messages:', error);
      }
    };

    fetchMessages();
  }, [sessionId, apiUrl]);

  // Scroll to bottom only when new user/bot messages are added or loading starts
  useEffect(() => {
    if (messages.length > 0) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [messages.length]);

  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || !sessionId || loading) return;

    const query = inputValue.trim();
    setInputValue('');
    setLoading(true);

    // Optimistically add user message
    const tempUserMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: mode === 'ship30' ? `Write a Ship 30 for 30 essay on: ${query}` : query,
      created_at: new Date().toISOString(),
      citations: [],
    };
    setMessages((prev) => [...prev, tempUserMessage]);

    try {
      if (mode === 'ship30') {
        const response = await axios.post(
          `${apiUrl}/sessions/${sessionId}/ship30`,
          { topic: query, stream: false },
          { timeout: 300000 }
        );

        if (response.data && response.data.essay) {
          const botMessage = {
            id: response.data.message_id || `asst-${Date.now()}`,
            role: 'assistant',
            content: response.data.essay,
            created_at: new Date().toISOString(),
            provider: 'ollama',
            model_name: 'llama3.2:3b',
            latency_ms: response.data.latency_ms,
            citations: [],
          };
          setMessages((prev) => {
            const filtered = prev.filter((m) => m.id !== tempUserMessage.id);
            return [...filtered, tempUserMessage, botMessage];
          });
        }

        // Notify right pane to refresh artifacts
        if (onArtifactCreated) {
          try { onArtifactCreated(); } catch (_) {}
        }
      } else {
        const response = await axios.post(
          `${apiUrl}/sessions/${sessionId}/messages`,
          { message: query, stream: false },
          { timeout: 300000 }
        );

        if (response.data && response.data.content) {
          const botMessage = {
            id: response.data.message_id || `asst-${Date.now()}`,
            role: 'assistant',
            content: response.data.content,
            created_at: new Date().toISOString(),
            provider: response.data.provider,
            model_name: response.data.model_name,
            latency_ms: response.data.latency_ms,
            retrieval_score: response.data.retrieval_score,
            citations: response.data.citations || [],
          };
          setMessages((prev) => {
            const filtered = prev.filter((m) => m.id !== tempUserMessage.id);
            return [...filtered, tempUserMessage, botMessage];
          });
        }
      }
    } catch (error) {
      console.warn('Chat request notice:', error);

      // Auto-recovery: Check if server completed and saved to DB
      try {
        const fallbackRes = await axios.get(`${apiUrl}/sessions/${sessionId}/messages`);
        if (fallbackRes.data && fallbackRes.data.length > 0) {
          const lastMsg = fallbackRes.data[fallbackRes.data.length - 1];
          if (lastMsg.role === 'assistant') {
            setMessages(fallbackRes.data);
            if (onArtifactCreated) {
              try { onArtifactCreated(); } catch (_) {}
            }
            return;
          }
        }
      } catch (_) {}

      const errorMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content:
          '⚠️ Sorry, I encountered an issue generating a response. Ensure Ollama is running and your database is connected.',
        created_at: new Date().toISOString(),
        error: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  if (!sessionId) {
    return (
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          p: 4,
          color: 'text.secondary',
        }}
      >
        <AutoAwesomeIcon sx={{ fontSize: 48, mb: 2, color: 'primary.light' }} />
        <Typography variant="h6">Select or create a conversation</Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          Ask questions grounded in Lenny's Podcast transcripts.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Top Header */}
      <Box
        sx={{
          px: 3,
          py: 1.5,
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          bgcolor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            {mode === 'ship30' ? '✍️ Ship 30 for 30 Essay Mode' : '💬 Grounded Q&A'}
          </Typography>
          <ButtonGroup size="small" variant="outlined">
            <Button
              variant={mode === 'qa' ? 'contained' : 'outlined'}
              onClick={() => setMode('qa')}
              startIcon={<ArticleIcon />}
            >
              Q&A
            </Button>
            <Button
              variant={mode === 'ship30' ? 'contained' : 'outlined'}
              onClick={() => setMode('ship30')}
              startIcon={<HistoryEduIcon />}
            >
              Ship 30
            </Button>
          </ButtonGroup>
        </Box>

        <Tooltip title="Close Session">
          <IconButton size="small" onClick={() => onSessionChange(null)}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Messages Scroll Area */}
      <Box sx={{ flex: 1, overflowY: 'auto', p: 3, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {messages.length === 0 && !loading && (
          <Box sx={{ textAlign: 'center', py: 8, color: 'text.secondary' }}>
            <Typography variant="h6" gutterBottom>
              {mode === 'ship30' ? 'Generate a structured Ship 30 essay' : 'What would you like to explore?'}
            </Typography>
            <Typography variant="body2">
              Try asking: "How did Figma find product-market fit?" or "What are Lenny's best tips for pricing?"
            </Typography>
          </Box>
        )}

        {messages.map((message) => {
          const isUser = message.role === 'user';
          return (
            <Box
              key={message.id}
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start',
              }}
            >
              <Paper
                elevation={isUser ? 0 : 1}
                sx={{
                  p: 2.5,
                  maxWidth: '85%',
                  borderRadius: 2.5,
                  bgcolor: isUser ? 'primary.main' : 'background.paper',
                  color: isUser ? 'primary.contrastText' : 'text.primary',
                  border: isUser ? 'none' : '1px solid',
                  borderColor: 'divider',
                }}
              >
                {/* Assistant metadata header */}
                {!isUser && !message.error && (
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mb: 1.5, flexWrap: 'wrap' }}>
                    <Chip
                      label={message.model_name || 'Ollama · llama3.2:3b'}
                      size="small"
                      color="primary"
                      variant="outlined"
                      sx={{ height: 22, fontSize: '0.75rem' }}
                    />
                    {message.retrieval_score !== undefined && message.retrieval_score !== null && (
                      <Chip
                        label={`Match: ${(message.retrieval_score * 100).toFixed(0)}%`}
                        size="small"
                        color={message.retrieval_score >= 0.5 ? 'success' : 'default'}
                        sx={{ height: 22, fontSize: '0.75rem' }}
                      />
                    )}
                    {message.latency_ms && (
                      <Typography variant="caption" sx={{ color: 'text.secondary', ml: 'auto' }}>
                        {(message.latency_ms / 1000).toFixed(1)}s
                      </Typography>
                    )}
                  </Box>
                )}

                {/* Content */}
                <Box sx={{ '& p': { m: 0, mb: 1 }, '& p:last-child': { mb: 0 } }}>
                  {isUser ? (
                    <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                      {message.content}
                    </Typography>
                  ) : (
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  )}
                </Box>

                {/* Citations List */}
                {!isUser && message.citations && message.citations.length > 0 && (
                  <Box sx={{ mt: 2, pt: 1.5, borderTop: '1px dashed', borderColor: 'divider' }}>
                    <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 0.5 }}>
                      📚 Sources Cited:
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap' }}>
                      {message.citations.map((c, cIdx) => (
                        <Chip
                          key={cIdx}
                          label={`${c.episode_title || 'Episode'} — ${c.guest_name || 'Guest'}`}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: '0.72rem', height: 24 }}
                        />
                      ))}
                    </Box>
                  </Box>
                )}
              </Paper>
            </Box>
          );
        })}

        {loading && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, p: 2 }}>
            <CircularProgress size={20} color="primary" />
            <Typography variant="body2" color="text.secondary">
              {mode === 'ship30'
                ? 'Synthesizing podcast insights and writing Ship 30 essay...'
                : 'Searching transcripts and reasoning...'}
            </Typography>
          </Box>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input Form */}
      <Box
        component="form"
        onSubmit={handleSendMessage}
        sx={{
          p: 2,
          borderTop: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
          display: 'flex',
          gap: 1.5,
          alignItems: 'center',
        }}
      >
        <TextField
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            mode === 'ship30'
              ? 'Enter essay topic (e.g. How to run user interviews that uncover real pain points)...'
              : 'Ask a growth or product question...'
          }
          fullWidth
          size="small"
          disabled={loading}
          autoFocus
        />
        <Button
          type="submit"
          variant="contained"
          color="primary"
          disabled={loading || !inputValue.trim()}
          endIcon={<SendIcon />}
          sx={{ minWidth: 100, px: 2 }}
        >
          {loading ? 'Thinking...' : 'Send'}
        </Button>
      </Box>
    </Box>
  );
};

export default ChatPane;
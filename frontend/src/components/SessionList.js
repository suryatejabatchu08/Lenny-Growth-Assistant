import React from 'react';
import { List, ListItemButton, ListItemText, IconButton, Typography, Box } from '@mui/material';
import AddCircleOutlinedIcon from '@mui/icons-material/AddCircleOutlined';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { useState } from 'react';

const SessionList = ({ sessions, currentSessionId, onSessionSelect, onNewSession }) => {
  const [hoveredSessionId, setHoveredSessionId] = useState(null);

  return (
    <div className="session-list">
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" color="text.primary">
          Sessions
        </Typography>
        <IconButton size="small" onClick={onNewSession} aria-label="New session">
          <AddCircleOutlinedIcon />
        </IconButton>
      </Box>
      <div sx={{ height: 'calc(100% - 56px)', overflowY: 'auto' }}>
        <List>
          {sessions.map((session) => (
            <ListItemButton
              key={session.id}
              onClick={() => onSessionSelect(session.id)}
              selected={session.id === currentSessionId}
              sx={{
                bgcolor: hoveredSessionId === session.id ? 'action.hover' : 'transparent',
                '&:hover': {
                  bgcolor: 'action.hover',
                },
                borderRadius: 1,
                mb: 1,
                px: 2,
              }}
              onMouseEnter={() => setHoveredSessionId(session.id)}
              onMouseLeave={() => setHoveredSessionId(null)}
            >
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                    <Typography variant="body1" sx={{ flexGrow: 1 }}>
                      {session.title || `Session ${session.id.substring(0, 8)}`}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      {new Date(session.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </Typography>
                  </Box>
                }
                secondary={
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    Updated
                  </Typography>
                }
              />
              {session.id !== currentSessionId && (
                <Box sx={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)' }}>
                  <ChevronRightIcon fontSize="small" color="action.disabled" />
                </Box>
              )}
            </ListItemButton>
          ))}
          {sessions.length === 0 && (
            <ListItemButton disabled sx={{ justifyContent: 'center', py: 3 }}>
              <Typography variant="body2" color="text.secondary">
                No sessions yet
              </Typography>
            </ListItemButton>
          )}
        </List>
      </div>
    </div>
  );
};

export default SessionList;
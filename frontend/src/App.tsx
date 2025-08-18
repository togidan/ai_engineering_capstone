import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Box, Container, Heading, VStack, HStack, Button } from '@chakra-ui/react'
import { Link, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Results from './pages/Results'
import Rfp from './pages/Rfp'
import Rag from './pages/Rag'
import KnowledgeBase from './pages/KnowledgeBase'

function Navigation() {
  const location = useLocation()
  
  const isActive = (path: string) => location.pathname === path
  
  return (
    <HStack spacing={4} justify="center" wrap="wrap">
      <Button 
        as={Link} 
        to="/" 
        variant={isActive('/') ? 'solid' : 'ghost'}
        colorScheme="blue"
      >
        City Scoring
      </Button>
      <Button 
        as={Link} 
        to="/rfp" 
        variant={isActive('/rfp') ? 'solid' : 'ghost'}
        colorScheme="blue"
      >
        RFP Analysis
      </Button>
      <Button 
        as={Link} 
        to="/rag" 
        variant={isActive('/rag') ? 'solid' : 'ghost'}
        colorScheme="blue"
      >
        RAG Search
      </Button>
      <Button 
        as={Link} 
        to="/kb" 
        variant={isActive('/kb') ? 'solid' : 'ghost'}
        colorScheme="blue"
      >
        Knowledge Base
      </Button>
    </HStack>
  )
}

function App() {
  return (
    <Router>
      <Box minH="100vh" bg="gray.50">
        <Container maxW="container.xl" py={8}>
          <VStack spacing={8} align="stretch">
            <Heading as="h1" size="xl" textAlign="center" color="blue.600">
              City Opportunity RAG MVP
            </Heading>
            
            <Navigation />
            
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/results" element={<Results />} />
              <Route path="/rfp" element={<Rfp />} />
              <Route path="/rag" element={<Rag />} />
              <Route path="/kb" element={<KnowledgeBase />} />
            </Routes>
          </VStack>
        </Container>
      </Box>
    </Router>
  )
}

export default App
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  VStack,
  Text,
  Button,
  Box,
  HStack,
  useColorModeValue,
  Input,
  List,
  ListItem,
  Spinner
} from '@chakra-ui/react';

interface City {
  city: string;
  state: string;
  pop: number;
  cbsa: string;
  median_income: number;
}

async function loadCities(): Promise<City[]> {
  const response = await fetch('/data/cities.csv');
  const csvText = await response.text();
  
  const lines = csvText.trim().split('\n');
  const headers = lines[0].split(',');
  
  return lines.slice(1).map(line => {
    const values = line.split(',');
    const city: any = {};
    
    headers.forEach((header, index) => {
      const value = values[index];
      
      if (header === 'city' || header === 'cbsa' || header === 'state') {
        city[header] = value;
      } else {
        city[header] = parseFloat(value);
      }
    });
    
    return city as City;
  });
}

export default function Home() {
  const [selectedCity, setSelectedCity] = useState<City | undefined>();
  const [cities, setCities] = useState<City[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredCities, setFilteredCities] = useState<City[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  
  const cardBg = useColorModeValue('white', 'gray.800');

  useEffect(() => {
    const fetchCities = async () => {
      try {
        const citiesData = await loadCities();
        setCities(citiesData);
        setFilteredCities(citiesData);
      } catch (error) {
        console.error('Failed to load cities:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCities();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      const filtered = cities.filter(city =>
        city.city.toLowerCase().includes(searchTerm.toLowerCase()) ||
        city.state.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredCities(filtered);
      setShowDropdown(true);
    } else {
      setFilteredCities(cities);
      setShowDropdown(false);
    }
  }, [searchTerm, cities]);

  const handleCitySelect = (city: City) => {
    setSelectedCity(city);
    setSearchTerm(`${city.city}, ${city.state}`);
    setShowDropdown(false);
  };

  const handleViewResults = () => {
    if (selectedCity) {
      navigate(`/results?city=${encodeURIComponent(selectedCity.city)}&state=${encodeURIComponent(selectedCity.state)}`);
    }
  };

  const handleGoToRfp = () => {
    navigate('/rfp');
  };

  return (
    <VStack spacing={8} align="stretch">
      <VStack spacing={4} textAlign="center">
        <Text fontSize="2xl" fontWeight="bold" color="blue.600">
          Discover City Opportunities
        </Text>
        <Text fontSize="lg" color="gray.600">
          Find the best industries and opportunities for your business in different cities
        </Text>
      </VStack>

      <Box p={8} bg={cardBg} borderRadius="lg" shadow="md">
        <VStack spacing={6} align="stretch">
          <Text fontSize="xl" fontWeight="semibold">
            Select a City
          </Text>
          
          {loading ? (
            <VStack spacing={2}>
              <Spinner size="md" />
              <Text fontSize="sm">Loading cities...</Text>
            </VStack>
          ) : (
            <Box position="relative">
              <Input
                placeholder="Search for a city..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onFocus={() => filteredCities.length > 0 && setShowDropdown(true)}
                size="lg"
              />
              
              {showDropdown && filteredCities.length > 0 && (
                <Box
                  position="absolute"
                  top="100%"
                  left={0}
                  right={0}
                  zIndex={10}
                  bg="white"
                  border="1px solid"
                  borderColor="gray.200"
                  borderRadius="md"
                  maxHeight="300px"
                  overflowY="auto"
                  mt={1}
                >
                  <List>
                    {filteredCities.slice(0, 10).map((city) => (
                      <ListItem
                        key={`${city.city}-${city.state}`}
                        p={3}
                        cursor="pointer"
                        _hover={{ bg: 'gray.50' }}
                        onClick={() => handleCitySelect(city)}
                        borderBottom="1px solid"
                        borderBottomColor="gray.200"
                      >
                        <Text fontWeight="medium">
                          {city.city}, {city.state}
                        </Text>
                        <Text fontSize="sm" color="gray.600">
                          Population: {city.pop.toLocaleString()} • 
                          Median Income: ${city.median_income.toLocaleString()}
                        </Text>
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Box>
          )}
          
          {selectedCity && (
            <>
              <Box p={4} bg="blue.50" borderRadius="md">
                <Text fontWeight="bold" color="blue.800">
                  Selected: {selectedCity.city}, {selectedCity.state}
                </Text>
                <Text fontSize="sm" color="blue.600">
                  Population: {selectedCity.pop.toLocaleString()} • 
                  CBSA: {selectedCity.cbsa}
                </Text>
              </Box>
              <Button
                colorScheme="blue"
                size="lg"
                onClick={handleViewResults}
                mt={4}
              >
                View Industry Opportunities
              </Button>
            </>
          )}
        </VStack>
      </Box>

      <HStack justify="center" pt={4}>
        <Text color="gray.600">or</Text>
      </HStack>

      <Box textAlign="center">
        <Text fontSize="lg" mb={4} color="gray.600">
          Have an RFP to analyze?
        </Text>
        <Button
          colorScheme="green"
          variant="outline"
          size="lg"
          onClick={handleGoToRfp}
        >
          RFP Workflow →
        </Button>
      </Box>
    </VStack>
  );
}
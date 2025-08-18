import { useState, useEffect } from 'react';
import {
  Box,
  Input,
  List,
  ListItem,
  Text,
  VStack,
  useColorModeValue,
  Spinner
} from '@chakra-ui/react';
import { City } from '../lib/types';

interface CitySelectProps {
  onCitySelect: (city: City) => void;
  selectedCity?: City;
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

export default function CitySelect({ onCitySelect, selectedCity }: CitySelectProps) {
  const [cities, setCities] = useState<City[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredCities, setFilteredCities] = useState<City[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverColor = useColorModeValue('gray.50', 'gray.700');

  useEffect(() => {
    const fetchCities = async () => {
      try {
        setLoading(true);
        setError('');
        const citiesData = await loadCities();
        setCities(citiesData);
        setFilteredCities(citiesData);
      } catch (error) {
        console.error('Failed to load cities:', error);
        setError('Failed to load cities');
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
    setSearchTerm(`${city.city}, ${city.state}`);
    setShowDropdown(false);
    onCitySelect(city);
  };

  const handleInputFocus = () => {
    if (filteredCities.length > 0) {
      setShowDropdown(true);
    }
  };

  if (loading) {
    return (
      <VStack spacing={2}>
        <Spinner size="md" />
        <Text fontSize="sm">Loading cities...</Text>
      </VStack>
    );
  }

  if (error) {
    return <Text color="red.500">{error}</Text>;
  }

  return (
    <VStack align="stretch" spacing={4}>
      <Box position="relative">
        <Input
          placeholder="Search for a city..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onFocus={handleInputFocus}
          size="lg"
          bg={bgColor}
        />
        
        {showDropdown && filteredCities.length > 0 && (
          <Box
            position="absolute"
            top="100%"
            left={0}
            right={0}
            zIndex={10}
            bg={bgColor}
            border="1px solid"
            borderColor={borderColor}
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
                  _hover={{ bg: hoverColor }}
                  onClick={() => handleCitySelect(city)}
                  borderBottom="1px solid"
                  borderBottomColor={borderColor}
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
      
      {selectedCity && (
        <Box p={4} bg="blue.50" borderRadius="md">
          <Text fontWeight="bold" color="blue.800">
            Selected: {selectedCity.city}, {selectedCity.state}
          </Text>
          <Text fontSize="sm" color="blue.600">
            Population: {selectedCity.pop.toLocaleString()} • 
            CBSA: {selectedCity.cbsa}
          </Text>
        </Box>
      )}
    </VStack>
  );
}
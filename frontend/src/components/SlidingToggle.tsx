import { Box, HStack, Text } from '@chakra-ui/react';

interface SlidingToggleProps {
  leftLabel: string;
  rightLabel: string;
  value: 'left' | 'right';
  onChange: (value: 'left' | 'right') => void;
  colorScheme?: string;
}

export default function SlidingToggle({
  leftLabel,
  rightLabel,
  value,
  onChange,
  colorScheme = 'blue'
}: SlidingToggleProps) {
  return (
    <Box
      position="relative"
      bg="gray.100"
      borderRadius="full"
      p={1}
      cursor="pointer"
      w="fit-content"
      border="1px solid"
      borderColor="gray.200"
    >
      {/* Background slider */}
      <Box
        position="absolute"
        top={1}
        left={value === 'left' ? 1 : '50%'}
        w="calc(50% - 2px)"
        h="calc(100% - 8px)"
        bg={`${colorScheme}.500`}
        borderRadius="full"
        transition="all 0.3s ease"
        boxShadow="sm"
      />
      
      <HStack spacing={0} position="relative" zIndex={1}>
        <Box
          px={6}
          py={2}
          onClick={() => onChange('left')}
          cursor="pointer"
          transition="all 0.3s ease"
        >
          <Text
            fontSize="sm"
            fontWeight="medium"
            color={value === 'left' ? 'white' : 'gray.600'}
            transition="color 0.3s ease"
            whiteSpace="nowrap"
          >
            {leftLabel}
          </Text>
        </Box>
        
        <Box
          px={6}
          py={2}
          onClick={() => onChange('right')}
          cursor="pointer"
          transition="all 0.3s ease"
        >
          <Text
            fontSize="sm"
            fontWeight="medium"
            color={value === 'right' ? 'white' : 'gray.600'}
            transition="color 0.3s ease"
            whiteSpace="nowrap"
          >
            {rightLabel}
          </Text>
        </Box>
      </HStack>
    </Box>
  );
}
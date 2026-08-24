/* App.js — SentiVox Mobile App Entry & Navigation Container */

import React, { useContext } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaView, StyleSheet } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';

import { AuthProvider, AuthContext } from './src/context/AuthContext';
import LoginScreen from './src/screens/LoginScreen';
import RegisterScreen from './src/screens/RegisterScreen';
import HomeScreen from './src/screens/HomeScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import AdminScreen from './src/screens/AdminScreen';

const Stack = createStackNavigator();

function Navigation() {
  const { user } = useContext(AuthContext);

  return (
    <NavigationContainer>
      <Stack.Navigator
        screenOptions={{
          headerShown: false,
          cardStyle: { backgroundColor: '#0B0F19' },
        }}
      >
        {!user ? (
          <>
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Register" component={RegisterScreen} />
          </>
        ) : (
          <>
            <Stack.Screen name="Home" component={HomeScreen} />
            <Stack.Screen name="History" component={HistoryScreen} />
            {user.role === 'ADMIN' ? (
              <Stack.Screen name="Admin" component={AdminScreen} />
            ) : null}
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <SafeAreaView style={styles.container}>
        <StatusBar style="light" />
        <Navigation />
      </SafeAreaView>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0F19',
  },
});

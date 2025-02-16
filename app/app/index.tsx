import { Text, View, StyleSheet } from "react-native";
import { Canvas, Circle, Group } from "@shopify/react-native-skia";


export default function Index() {

    const width = 256;
    const height = 256;
    const r = width * 0.33;

    return ( 
        <View style={styles.container}>
            <View
            style={styles.container}>
                <Canvas style={{width, height}}>
                    <Group blendMode="multiply">
                        <Circle cx={r} cy={r} r={r} color="cyan" />
                        <Circle cx={width - r} cy={r} r={r} color="magenta" />
                        <Circle cx={width / 2} cy={width - r} r={r} color="yellow" />
                    </Group>
                </Canvas>
            </View>
        </View>
    );
}

const styles = StyleSheet.create(
   {
    container: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center"
    }
    }
);
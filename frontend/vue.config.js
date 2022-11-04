module.exports = {
    runtimeCompiler: true,
    devServer: {
        proxy: 'https://127.0.0.1:8081',
        https: true,
        port: 8081
    }
}

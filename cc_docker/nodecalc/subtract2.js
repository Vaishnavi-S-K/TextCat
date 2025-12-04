const express = require('express')
const app = express()

app.get('/subtract/', (req, res) => {
    const [num1, num2] = req.query.id.split(' ')
    const total = (+num1) - (+num2)
    res.send('The answer is: ' + total)
})

app.listen(3001, () => console.log('Subtraction on 3001'))


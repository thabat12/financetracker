Lessons I learned (from testing v1):
<ul>
    <li>
        Using a local test client for the API is too detached and convoluted from the main API
    </li>
    <li> Local testing is also restrictive in the ways that it replicates real-world scenarios, where this API is deployed to the cloud and interacts with several other components over the network.
    </li>
    <li> Finally, the scope of local testing slows down implementation because you are testing very small components of the entire system and not placing enough time on larger-scale components like caching or batch scripts, which eventually require integration testing anyways.
    </li>

</ul>

So yeah, now we at testing v2:

For all these reasons, local testing now emphasizes integration testing, where each component of the application: the database, API, cache layer, batch scripts, and testing clients, are all modularized through Docker containers. With this method, testing is able to reflect a more real-world scenario where this backend is actually deployed in a cloud environment.

However, for this method to be possible, there must be changes to the API and database logic. There is a new and slightly modified version of the original API, the test API, which allows for test clients to make custom users and bypass some of the more stringent security requirements in the regular authorization pipeline. This allows for better automated testing for the actual key elements of the API pipeline.

Overall, the main idea is: Dockerize everything. After everything is modularized through their own containers, each service then has a way to interact with and perform its own, isolated tasks.